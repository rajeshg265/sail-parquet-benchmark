#!/usr/bin/env python3
"""
Spark-only worker script — run via subprocess so it starts in a clean
Python process with no pysail module state. Writes JSON results to stdout.
"""
import os, sys, json, time, statistics
from pathlib import Path

# Clear any SparkConnect env vars inherited from pysail parent process
for _k in ["SPARK_REMOTE", "SPARK_CONNECT_MODE_ENABLED"]:
    os.environ.pop(_k, None)

DATA_DIR = os.environ.get("BENCHMARK_DATA_DIR") or str(Path(__file__).parent / "data")
N_RUNS   = 10
PARQUET1_VIEW = "frtb_sa_capital_output"

FRTB_QUERIES = [
    ("scan_only_count",
     f"""SELECT COUNT(*) FROM {PARQUET1_VIEW}"""),

    ("scan_only_sum1col",
     f"""SELECT SUM(total) FROM {PARQUET1_VIEW}"""),

    ("full_agg",
     f"""SELECT SUM(commodities_delta+commodities_vega+commodities_curvature) AS commodities_sa,
                SUM(equities_delta+equities_vega+equities_curvature) AS equities_sa,
                SUM(interest_rates_delta+interest_rates_vega+interest_rates_curvature) AS rates_sa,
                SUM(foreign_exchange_delta+foreign_exchange_vega+foreign_exchange_curvature) AS fx_sa
         FROM {PARQUET1_VIEW}"""),

    ("grouped_agg",
     f"""SELECT legal_entity_group_id, correlation_scenario_id, driving_scenario,
                SUM(total) AS total_capital, COUNT(*) AS row_count
         FROM {PARQUET1_VIEW}
         GROUP BY legal_entity_group_id, correlation_scenario_id, driving_scenario
         ORDER BY total_capital DESC LIMIT 20"""),

    ("filtered_agg",
     f"""SELECT legal_entity_group_id, SUM(total) AS total_capital,
                SUM(equities_delta) AS eq_delta, SUM(interest_rates_delta) AS ir_delta
         FROM {PARQUET1_VIEW} WHERE legal_entity_group_id < 17
         GROUP BY legal_entity_group_id ORDER BY total_capital DESC LIMIT 20"""),

    ("join_entity",
     f"""SELECT e.region, e.business_unit, SUM(f.total) AS total_capital, COUNT(*) AS row_count
         FROM {PARQUET1_VIEW} f
         JOIN entity_hierarchy e ON f.legal_entity_group_id = e.legal_entity_group_id
         GROUP BY e.region, e.business_unit ORDER BY total_capital DESC"""),

    ("join_desk",
     f"""SELECT c.desk_name, c.risk_pillar, SUM(f.total) AS total_capital, SUM(f.rrao) AS rrao_charge
         FROM {PARQUET1_VIEW} f
         JOIN chorushierarchy c ON f.node_id = c.node_id
         GROUP BY c.desk_name, c.risk_pillar ORDER BY total_capital DESC LIMIT 20"""),

    ("join_calendar",
     f"""SELECT d.fiscal_year, d.fiscal_quarter, SUM(f.total) AS total_capital
         FROM {PARQUET1_VIEW} f
         JOIN cobdate d ON f.cobdate = d.cobdate
         GROUP BY d.fiscal_year, d.fiscal_quarter
         ORDER BY d.fiscal_year, d.fiscal_quarter"""),
]

os.environ["SPARK_LOCAL_IP"]   = "127.0.0.1"
os.environ["PYSPARK_PYTHON"]   = sys.executable

from pyspark.sql import SparkSession

spark = (SparkSession.builder
         .master("local-cluster[3,1,1024]")
         .appName("bench_parquet_cluster_spark")
         .config("spark.driver.host",                "127.0.0.1")
         .config("spark.driver.bindAddress",         "127.0.0.1")
         .config("spark.sql.shuffle.partitions",     "3")
         .config("spark.sql.adaptive.enabled",       "true")
         .config("spark.sql.parquet.filterPushdown", "true")
         .config("spark.ui.enabled",                 "false")
         .config("spark.driver.memory",              "2g")
         .config("spark.executor.memory",            "1g")
         .getOrCreate())
spark.sparkContext.setLogLevel("WARN")

spark.read.parquet(f"{DATA_DIR}/entity_hierarchy.parquet").createOrReplaceTempView("entity_hierarchy")
spark.read.parquet(f"{DATA_DIR}/chorushierarchy.parquet").createOrReplaceTempView("chorushierarchy")
spark.read.parquet(f"{DATA_DIR}/cobdate.parquet").createOrReplaceTempView("cobdate")
spark.read.parquet(
    f"{DATA_DIR}/parquet1.parquet",
    f"{DATA_DIR}/parquet2.parquet",
).createOrReplaceTempView(PARQUET1_VIEW)
print("Tables registered (parquet1 + parquet2 combined, 54.88M rows).", file=sys.stderr, flush=True)

results = {}
for qid, sql in FRTB_QUERIES:
    print(f"\n  [{qid}]", file=sys.stderr, flush=True)
    try: spark.sql(sql).collect()
    except Exception: pass
    times = []
    for _ in range(N_RUNS):
        t0 = time.time()
        try:
            spark.sql(sql).collect()
            times.append(round((time.time() - t0) * 1000, 1))
        except Exception as e:
            print(f"    run failed: {e}", file=sys.stderr, flush=True)
    if times:
        med = round(statistics.median(times), 1)
        p99 = sorted(times)[max(0, int(len(times) * 0.99) - 1)]
        print(f"    median={med:>7.0f}ms  p99={p99:>7.0f}ms  all={[round(t) for t in times]}", file=sys.stderr, flush=True)
        results[qid] = {"median_ms": med, "p99_ms": p99, "times_ms": times}
    else:
        print(f"    all runs failed — skipping", file=sys.stderr, flush=True)
        results[qid] = {"median_ms": None, "p99_ms": None, "times_ms": [], "error": "all runs failed"}

# Print results BEFORE stopping Spark — the JVM may exit non-zero during
# shutdown (Netty connection-reset on Windows) which would prevent the print.
print(json.dumps(results))
sys.stdout.flush()

try:
    spark.stop()
except Exception:
    pass

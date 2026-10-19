# sail-parquet-benchmark

Benchmarks comparing [pysail](https://github.com/lakehq/sail) (DataFusion/Rust engine) against Apache Spark 4.2.0 on a synthetic FRTB SA capital output dataset.

**Dataset**: 54.88 million rows · 9.71 GB · 2 Parquet files · 32 columns of float64 risk data  
**Topology**: Sail `local-cluster` (3 Tokio workers, 1 Rust process) vs Spark `local-cluster[3,1,1024]` (3 executor JVMs)

## Results summary

| Query | Sail P99 | Spark P99 | Speedup |
|---|---|---|---|
| full_agg | 5,628 ms | 14,144 ms | 2.5× |
| grouped_agg | 2,725 ms | 5,266 ms | 1.9× |
| filtered_agg | 2,473 ms | 5,069 ms | 2.0× |
| join_entity | 5,960 ms | 16,027 ms | 2.7× |
| join_desk | 5,695 ms | 13,401 ms | 2.4× |
| join_calendar | 5,668 ms | 7,770 ms | 1.4× |

Measured on Apple M1, 10-run medians. See [benchmark artifact](https://claude.ai/artifact/HFc8hocrtX2ADQTEBaWZp7) for full analysis.

## Requirements

```
pip install pysail pyspark pyarrow
```

- Python 3.10+
- Java 11+ (for Spark)
- ~12 GB free disk space (for generated data)
- ~8 GB RAM recommended

## Quickstart

**Step 1 — generate the data** (takes ~10 minutes, runs once):

```bash
python infra/generate_data.py
```

This creates `data/parquet1.parquet`, `data/parquet2.parquet`, and three lookup tables (~9.7 GB total).

**Step 2 — run the benchmark**:

```bash
# Both engines
python bench_cluster.py

# Sail only
python bench_cluster.py --sail-only

# Spark only
python bench_cluster.py --spark-only
```

Results are saved to `results/results_<timestamp>.json`.

## Files

| File | Description |
|---|---|
| `infra/generate_data.py` | Generates synthetic FRTB Parquet data |
| `bench_cluster.py` | Main benchmark — Sail vs Spark, 6 queries, 10 runs each |
| `_bench_spark_worker.py` | Spark subprocess worker (isolated from pysail state) |
| `bench_profile.py` | Profiling benchmark with GC metrics, EXPLAIN ANALYZE, isolation queries |
| `_bench_spark_profile_worker.py` | Spark subprocess worker for profiling |
| `_spark_local_vs_cluster.py` | Isolation: Spark `local[3]` vs `local-cluster[3,1,1024]` overhead |

## Dataset schema

FRTB SA capital output — 32 columns including:
- Risk charges by asset class: `commodities_*`, `equities_*`, `interest_rates_*`, `foreign_exchange_*` (delta/vega/curvature)
- Dimensions: `cobdate`, `legal_entity_group_id`, `node_id`, `driving_scenario`, `correlation_scenario_id`
- Lookup tables: `entity_hierarchy`, `chorushierarchy`, `cobdate`

All data is synthetic (random seed 42). No real financial data.

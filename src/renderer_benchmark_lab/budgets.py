def evaluate(aggregate: dict, budgets: dict, baseline: dict | None = None) -> list[dict]:
    checks = []
    def add(name, actual, limit):
        checks.append({"name": name, "actual": actual, "limit": limit, "passed": actual <= limit})
    if "max_error_percent" in budgets:
        add("overall error", aggregate["overall_error_percent"], budgets["max_error_percent"])
    if "max_critical_failures" in budgets:
        add("critical failures", aggregate["critical_failure_count"], budgets["max_critical_failures"])
    if baseline and "max_quality_regression" in budgets:
        regression = baseline["quality_score"] - aggregate["quality_score"]
        add("quality regression", regression, budgets["max_quality_regression"])
    if baseline and "max_speed_regression_percent" in budgets:
        regression = (aggregate["candidate_median_ms"] / max(.001, baseline["candidate_median_ms"]) - 1) * 100
        add("speed regression", regression, budgets["max_speed_regression_percent"])
    return checks


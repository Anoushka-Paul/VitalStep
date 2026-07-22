/// Cohort reference interval returned by the server-side quantile model.
class ForceReference {
  final double p05Kg;
  final double p50Kg;
  final double p95Kg;

  const ForceReference({
    required this.p05Kg,
    required this.p50Kg,
    required this.p95Kg,
  });

  factory ForceReference.fromJson(Map<String, dynamic> json) => ForceReference(
        p05Kg: (json['p05_kg'] as num).toDouble(),
        p50Kg: (json['p50_kg'] as num).toDouble(),
        p95Kg: (json['p95_kg'] as num).toDouble(),
      );
}

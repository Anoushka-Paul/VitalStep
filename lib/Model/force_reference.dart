/// Cohort reference interval returned by the server-side quantile model.
class ForceReference {
  final double? p05Kg;
  final double? p50Kg;
  final double? p95Kg;
  final String flag;
  final String modelSource;
  final List<String> recommendations;

  const ForceReference({
    required this.p05Kg,
    required this.p50Kg,
    required this.p95Kg,
    required this.flag,
    required this.modelSource,
    required this.recommendations,
  });

  factory ForceReference.fromJson(Map<String, dynamic> json) => ForceReference(
        p05Kg: (json['expected_lower_kg'] as num?)?.toDouble(),
        p50Kg: (json['expected_median_kg'] as num?)?.toDouble(),
        p95Kg: (json['expected_upper_kg'] as num?)?.toDouble(),
        flag: json['predicted_category'] as String,
        modelSource: json['model_source'] as String,
        recommendations: List<String>.from(json['recommendations'] as List),
      );
}

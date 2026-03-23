enum ReconstructionStage {
  pending,
  auditing,
  segmenting,
  mapping,
  training,
  librarian,
  completed,
  failed
}

class ReconstructionProgress {
  final ReconstructionStage stage;
  final double progress;
  final String message;

  ReconstructionProgress({
    required this.stage,
    required this.progress,
    required this.message,
  });

  factory ReconstructionProgress.initial() {
    return ReconstructionProgress(
      stage: ReconstructionStage.pending,
      progress: 0.0,
      message: 'Initialising...',
    );
  }

  factory ReconstructionProgress.fromMap(Map<String, dynamic> map) {
    return ReconstructionProgress(
      stage: ReconstructionStage.values.firstWhere(
        (e) => e.name == (map['status'] as String).toLowerCase(),
        orElse: () => ReconstructionStage.pending,
      ),
      progress: (double.tryParse(map['progressPercentage']?.toString() ?? '0') ?? 0) / 100.0,
      message: map['currentStage'] ?? 'Processing...',
    );
  }
}

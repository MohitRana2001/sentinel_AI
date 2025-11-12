/**
 * Format seconds to human-readable time (e.g., "12s", "1m34s", "2h15m")
 */
export function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  
  if (minutes < 60) {
    return remainingSeconds > 0 
      ? `${minutes}m${remainingSeconds}s`
      : `${minutes}m`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  if (remainingMinutes > 0) {
    return `${hours}h${remainingMinutes}m`;
  }
  
  return `${hours}h`;
}

/**
 * Format processing stages for display
 */
export function formatProcessingStages(stages: Record<string, number>): string {
  if (!stages || Object.keys(stages).length === 0) {
    return "No timing data";
  }
  
  const entries = Object.entries(stages);
  return entries
    .map(([stage, time]) => `${formatStageName(stage)}: ${formatTime(time)}`)
    .join(", ");
}

/**
 * Convert snake_case stage names to readable format
 */
function formatStageName(stage: string): string {
  return stage
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get total processing time from stages
 */
export function getTotalTime(stages: Record<string, number>): number {
  return Object.values(stages).reduce((sum, time) => sum + time, 0);
}

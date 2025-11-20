"""
Progress Tracking and Visualization
Comprehensive progress tracking with charts, statistics, and learning analytics.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import numpy as np


class ProgressTracker:
    """Track and visualize training progress over time"""
    
    def __init__(self, training_data_dir: Path):
        self.training_data_dir = training_data_dir
        self.progress_file = training_data_dir / "progress.json"
        self.sessions_dir = training_data_dir / "sessions"
        self.charts_dir = training_data_dir / "charts"
        
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load progress data"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        
        return {
            'current_level': 1,
            'completed_tasks': 0,
            'total_score': 0.0,
            'best_scores': {},
            'session_history': []
        }
    
    def generate_progress_report(self) -> str:
        """Generate comprehensive progress report"""
        report = []
        report.append("="*70)
        report.append("TRAINING PROGRESS REPORT")
        report.append("="*70)
        report.append("")
        
        # Overall statistics
        total_tasks = self.progress['completed_tasks']
        avg_score = self.progress['total_score'] / max(1, total_tasks)
        
        report.append("📊 OVERALL STATISTICS")
        report.append(f"   Total Tasks Completed: {total_tasks}")
        report.append(f"   Average Score: {avg_score:.1f}/100")
        report.append(f"   Current Level: {self.progress['current_level']}")
        report.append(f"   Total Training Time: {self._calculate_total_time()}")
        report.append("")
        
        # Performance by task type
        if self.progress['best_scores']:
            report.append("🏆 PERFORMANCE BY TASK TYPE")
            for task_type, score in sorted(self.progress['best_scores'].items(), 
                                          key=lambda x: x[1], reverse=True):
                bar = self._create_progress_bar(score, 100, width=30)
                report.append(f"   {task_type:20s} {bar} {score:.1f}/100")
            report.append("")
        
        # Recent performance
        recent = self.progress['session_history'][-10:]
        if recent:
            report.append("📈 RECENT PERFORMANCE (Last 10 Tasks)")
            for entry in recent:
                score = entry['score']
                task_id = entry['task_id']
                timestamp = entry.get('timestamp', '')[:19]  # Trim to datetime
                
                emoji = "🟢" if score >= 85 else "🟡" if score >= 70 else "🔴"
                report.append(f"   {emoji} {task_id:30s} {score:5.1f}/100  {timestamp}")
            report.append("")
        
        # Learning trends
        if len(self.progress['session_history']) >= 5:
            trend = self._analyze_learning_trend()
            report.append("📊 LEARNING TREND")
            report.append(f"   {trend['description']}")
            report.append(f"   Improvement Rate: {trend['improvement_rate']:.2f} points/task")
            report.append("")
        
        # Milestones
        milestones = self._check_milestones()
        if milestones:
            report.append("🎯 MILESTONES ACHIEVED")
            for milestone in milestones:
                report.append(f"   ✓ {milestone}")
            report.append("")
        
        # Next goals
        goals = self._suggest_next_goals()
        if goals:
            report.append("🎯 NEXT GOALS")
            for goal in goals:
                report.append(f"   • {goal}")
            report.append("")
        
        report.append("="*70)
        
        return "\n".join(report)
    
    def _create_progress_bar(self, value: float, max_value: float, width: int = 20) -> str:
        """Create ASCII progress bar"""
        filled = int((value / max_value) * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"
    
    def _calculate_total_time(self) -> str:
        """Calculate total training time from sessions"""
        if not self.sessions_dir.exists():
            return "0h 0m"
        
        total_seconds = 0
        
        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            for session_file in session_dir.glob("*_session.json"):
                with open(session_file, 'r') as f:
                    data = json.load(f)
                
                exec_time = data.get('result', {}).get('execution_time_seconds', 0)
                total_seconds += exec_time
        
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return f"{hours}h {minutes}m"
    
    def _analyze_learning_trend(self) -> Dict:
        """Analyze learning trend over time"""
        history = self.progress['session_history']
        
        if len(history) < 5:
            return {'description': 'Insufficient data', 'improvement_rate': 0.0}
        
        # Get scores
        scores = [entry['score'] for entry in history]
        
        # Calculate linear regression
        x = np.arange(len(scores))
        y = np.array(scores)
        
        # Fit line
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        # Determine trend
        if slope > 2:
            description = "📈 Strong improvement - excellent progress!"
        elif slope > 0.5:
            description = "📈 Steady improvement - keep practicing"
        elif slope > -0.5:
            description = "➡️  Stable performance - consistent results"
        elif slope > -2:
            description = "📉 Slight decline - review fundamentals"
        else:
            description = "📉 Declining - need to refocus"
        
        return {
            'description': description,
            'improvement_rate': float(slope)
        }
    
    def _check_milestones(self) -> List[str]:
        """Check which milestones have been achieved"""
        milestones = []
        
        total_tasks = self.progress['completed_tasks']
        avg_score = self.progress['total_score'] / max(1, total_tasks)
        
        # Task count milestones
        if total_tasks >= 100:
            milestones.append("Century Club - 100+ tasks completed")
        elif total_tasks >= 50:
            milestones.append("Half Century - 50+ tasks completed")
        elif total_tasks >= 10:
            milestones.append("Getting Started - 10+ tasks completed")
        
        # Score milestones
        if avg_score >= 90:
            milestones.append("Master - 90+ average score")
        elif avg_score >= 85:
            milestones.append("Expert - 85+ average score")
        elif avg_score >= 80:
            milestones.append("Proficient - 80+ average score")
        
        # Perfect scores
        perfect_scores = sum(1 for entry in self.progress['session_history'] 
                           if entry['score'] >= 95)
        if perfect_scores >= 5:
            milestones.append(f"Perfectionist - {perfect_scores} near-perfect scores")
        
        return milestones
    
    def _suggest_next_goals(self) -> List[str]:
        """Suggest next training goals"""
        goals = []
        
        total_tasks = self.progress['completed_tasks']
        avg_score = self.progress['total_score'] / max(1, total_tasks)
        current_level = self.progress['current_level']
        
        # Level progression
        if avg_score >= 85 and current_level < 4:
            goals.append(f"Advance to Level {current_level + 1}")
        elif avg_score < 80:
            goals.append(f"Improve average score to 80+ (current: {avg_score:.1f})")
        
        # Task-specific goals
        for task_type, score in self.progress['best_scores'].items():
            if score < 80:
                goals.append(f"Master {task_type} (current best: {score:.1f})")
        
        # Volume goals
        if total_tasks < 50:
            goals.append(f"Complete {50 - total_tasks} more tasks to reach 50 total")
        
        # Consistency goals
        recent_scores = [e['score'] for e in self.progress['session_history'][-10:]]
        if recent_scores and np.std(recent_scores) > 15:
            goals.append("Improve consistency - reduce score variation")
        
        return goals[:5]  # Top 5 goals
    
    def plot_progress_over_time(self, output_file: Optional[Path] = None):
        """Generate progress chart over time"""
        if not self.progress['session_history']:
            print("No data to plot")
            return
        
        # Extract data
        timestamps = []
        scores = []
        
        for entry in self.progress['session_history']:
            try:
                ts = datetime.fromisoformat(entry['timestamp'])
                timestamps.append(ts)
                scores.append(entry['score'])
            except:
                continue
        
        if not timestamps:
            print("No valid timestamps")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot scores
        ax.plot(timestamps, scores, 'o-', linewidth=2, markersize=6, label='Task Score')
        
        # Add moving average
        if len(scores) >= 5:
            window = min(5, len(scores))
            moving_avg = np.convolve(scores, np.ones(window)/window, mode='valid')
            ma_timestamps = timestamps[window-1:]
            ax.plot(ma_timestamps, moving_avg, '--', linewidth=2, 
                   label=f'{window}-Task Moving Average', alpha=0.7)
        
        # Add reference lines
        ax.axhline(y=85, color='g', linestyle=':', alpha=0.5, label='Expert (85)')
        ax.axhline(y=70, color='orange', linestyle=':', alpha=0.5, label='Acceptable (70)')
        
        # Formatting
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('Training Progress Over Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_ylim(0, 105)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save
        if output_file is None:
            output_file = self.charts_dir / "progress_over_time.png"
        
        plt.savefig(output_file, dpi=150)
        print(f"Chart saved to: {output_file}")
        plt.close()
    
    def plot_task_type_performance(self, output_file: Optional[Path] = None):
        """Generate bar chart of performance by task type"""
        if not self.progress['best_scores']:
            print("No task type data to plot")
            return
        
        # Extract data
        task_types = list(self.progress['best_scores'].keys())
        scores = list(self.progress['best_scores'].values())
        
        # Sort by score
        sorted_data = sorted(zip(task_types, scores), key=lambda x: x[1], reverse=True)
        task_types, scores = zip(*sorted_data)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create bars with color coding
        colors = ['green' if s >= 85 else 'orange' if s >= 70 else 'red' for s in scores]
        bars = ax.barh(task_types, scores, color=colors, alpha=0.7)
        
        # Add value labels
        for i, (bar, score) in enumerate(zip(bars, scores)):
            ax.text(score + 1, i, f'{score:.1f}', va='center')
        
        # Add reference lines
        ax.axvline(x=85, color='g', linestyle=':', alpha=0.5, label='Expert')
        ax.axvline(x=70, color='orange', linestyle=':', alpha=0.5, label='Acceptable')
        
        # Formatting
        ax.set_xlabel('Best Score', fontsize=12)
        ax.set_ylabel('Task Type', fontsize=12)
        ax.set_title('Performance by Task Type', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 105)
        ax.grid(True, alpha=0.3, axis='x')
        ax.legend()
        
        plt.tight_layout()
        
        # Save
        if output_file is None:
            output_file = self.charts_dir / "task_type_performance.png"
        
        plt.savefig(output_file, dpi=150)
        print(f"Chart saved to: {output_file}")
        plt.close()
    
    def plot_score_distribution(self, output_file: Optional[Path] = None):
        """Generate histogram of score distribution"""
        if not self.progress['session_history']:
            print("No data to plot")
            return
        
        scores = [entry['score'] for entry in self.progress['session_history']]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create histogram
        n, bins, patches = ax.hist(scores, bins=20, edgecolor='black', alpha=0.7)
        
        # Color code bins
        for i, patch in enumerate(patches):
            bin_center = (bins[i] + bins[i+1]) / 2
            if bin_center >= 85:
                patch.set_facecolor('green')
            elif bin_center >= 70:
                patch.set_facecolor('orange')
            else:
                patch.set_facecolor('red')
        
        # Add statistics
        mean_score = np.mean(scores)
        median_score = np.median(scores)
        
        ax.axvline(mean_score, color='blue', linestyle='--', linewidth=2, 
                  label=f'Mean: {mean_score:.1f}')
        ax.axvline(median_score, color='purple', linestyle='--', linewidth=2,
                  label=f'Median: {median_score:.1f}')
        
        # Formatting
        ax.set_xlabel('Score', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('Score Distribution', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend()
        
        plt.tight_layout()
        
        # Save
        if output_file is None:
            output_file = self.charts_dir / "score_distribution.png"
        
        plt.savefig(output_file, dpi=150)
        print(f"Chart saved to: {output_file}")
        plt.close()
    
    def generate_all_charts(self):
        """Generate all progress charts"""
        print("Generating progress charts...")
        self.plot_progress_over_time()
        self.plot_task_type_performance()
        self.plot_score_distribution()
        print(f"\nAll charts saved to: {self.charts_dir}")


if __name__ == '__main__':
    import sys
    
    workspace = Path(__file__).parent
    training_data_dir = workspace / "training_data"
    
    tracker = ProgressTracker(training_data_dir)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--charts':
        # Generate charts
        tracker.generate_all_charts()
    else:
        # Print progress report
        report = tracker.generate_progress_report()
        print(report)

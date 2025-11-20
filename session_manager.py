"""
Session Manager - Resume training from previous sessions
Analyzes past performance and provides context for continued learning
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class SessionManager:
    """Manages training session continuity across context resets"""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.training_data_dir = workspace_dir / "training_data"
        self.sessions_dir = self.training_data_dir / "sessions"
        self.progress_file = self.training_data_dir / "progress.json"
        
    def get_resume_briefing(self) -> str:
        """
        Generate a comprehensive briefing for resuming training.
        This allows the AI to quickly understand past performance when context resets.
        """
        if not self.progress_file.exists():
            return "No previous training sessions found. Starting fresh!"
        
        with open(self.progress_file, 'r') as f:
            progress = json.load(f)
        
        briefing = []
        briefing.append("="*70)
        briefing.append("TRAINING RESUME BRIEFING")
        briefing.append("="*70)
        briefing.append("")
        
        # Overall stats
        total_tasks = progress.get('completed_tasks', 0)
        avg_score = progress.get('total_score', 0) / max(1, total_tasks)
        current_level = progress.get('current_level', 1)
        
        briefing.append(f"📊 OVERALL PROGRESS:")
        briefing.append(f"   • Total tasks completed: {total_tasks}")
        briefing.append(f"   • Average score: {avg_score:.1f}/100")
        briefing.append(f"   • Current level: {current_level}")
        briefing.append("")
        
        # Best scores by task type
        best_scores = progress.get('best_scores', {})
        if best_scores:
            briefing.append("🏆 BEST SCORES BY TASK TYPE:")
            for task_type, score in sorted(best_scores.items(), key=lambda x: x[1], reverse=True):
                briefing.append(f"   • {task_type}: {score:.1f}/100")
            briefing.append("")
        
        # Recent session history
        recent_sessions = progress.get('session_history', [])[-10:]
        if recent_sessions:
            briefing.append("📈 RECENT PERFORMANCE (last 10 tasks):")
            for session in recent_sessions:
                task_id = session.get('task_id', 'unknown')
                score = session.get('score', 0)
                timestamp = session.get('timestamp', '')
                briefing.append(f"   • {task_id}: {score:.1f}/100 ({timestamp})")
            briefing.append("")
        
        # Performance trends
        if len(recent_sessions) >= 5:
            recent_scores = [s.get('score', 0) for s in recent_sessions[-5:]]
            trend = self._analyze_trend(recent_scores)
            briefing.append(f"📊 RECENT TREND: {trend}")
            briefing.append("")
        
        # Strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(best_scores)
        
        if strengths:
            briefing.append("💪 STRENGTHS:")
            for strength in strengths:
                briefing.append(f"   • {strength}")
            briefing.append("")
        
        if weaknesses:
            briefing.append("⚠️  AREAS FOR IMPROVEMENT:")
            for weakness in weaknesses:
                briefing.append(f"   • {weakness}")
            briefing.append("")
        
        # Recommendations
        recommendations = self._generate_recommendations(progress)
        if recommendations:
            briefing.append("💡 RECOMMENDATIONS:")
            for rec in recommendations:
                briefing.append(f"   • {rec}")
            briefing.append("")
        
        briefing.append("="*70)
        
        return "\n".join(briefing)
    
    def _analyze_trend(self, scores: List[float]) -> str:
        """Analyze performance trend"""
        if len(scores) < 2:
            return "Insufficient data"
        
        # Simple linear trend
        avg_first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
        avg_second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        
        diff = avg_second_half - avg_first_half
        
        if diff > 5:
            return f"📈 Improving (+{diff:.1f} points)"
        elif diff < -5:
            return f"📉 Declining ({diff:.1f} points)"
        else:
            return f"➡️  Stable (~{diff:.1f} points)"
    
    def _identify_strengths_weaknesses(self, best_scores: Dict) -> tuple:
        """Identify strengths and weaknesses based on scores"""
        strengths = []
        weaknesses = []
        
        for task_type, score in best_scores.items():
            if score >= 90:
                strengths.append(f"{task_type} (mastered at {score:.1f}/100)")
            elif score >= 80:
                strengths.append(f"{task_type} (proficient at {score:.1f}/100)")
            elif score < 70:
                weaknesses.append(f"{task_type} (struggling at {score:.1f}/100)")
        
        return strengths, weaknesses
    
    def _generate_recommendations(self, progress: Dict) -> List[str]:
        """Generate training recommendations"""
        recommendations = []
        
        total_tasks = progress.get('completed_tasks', 0)
        avg_score = progress.get('total_score', 0) / max(1, total_tasks)
        current_level = progress.get('current_level', 1)
        best_scores = progress.get('best_scores', {})
        
        # Level progression
        if avg_score >= 85 and current_level < 4:
            recommendations.append(f"Ready to advance to Level {current_level + 1}")
        elif avg_score < 75:
            recommendations.append(f"Continue practicing Level {current_level} tasks")
        
        # Task-specific recommendations
        for task_type, score in best_scores.items():
            if score < 70:
                recommendations.append(f"Focus on improving {task_type} (current best: {score:.1f})")
        
        # Volume recommendations
        if total_tasks < 20:
            recommendations.append("Complete more tasks to build consistency (target: 20+ tasks)")
        
        return recommendations
    
    def get_last_session_summary(self) -> Optional[Dict]:
        """Get summary of the most recent session"""
        if not self.sessions_dir.exists():
            return None
        
        # Find most recent session directory
        session_dirs = sorted([d for d in self.sessions_dir.iterdir() if d.is_dir()])
        if not session_dirs:
            return None
        
        last_session_dir = session_dirs[-1]
        
        # Load all session files
        session_files = list(last_session_dir.glob("*_session.json"))
        
        if not session_files:
            return None
        
        summary = {
            'session_id': last_session_dir.name,
            'task_count': len(session_files),
            'tasks': []
        }
        
        total_score = 0
        
        for session_file in session_files:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            task_id = session_data['task']['task_id']
            score = session_data['analysis']['feedback']['overall_score']
            total_score += score
            
            summary['tasks'].append({
                'task_id': task_id,
                'description': session_data['task']['description'],
                'score': score
            })
        
        summary['average_score'] = total_score / len(session_files)
        
        return summary
    
    def export_learning_summary(self, output_file: Optional[Path] = None) -> str:
        """
        Export a comprehensive learning summary for review.
        This can be read at the start of a new session to quickly catch up.
        """
        if output_file is None:
            output_file = self.training_data_dir / "learning_summary.md"
        
        summary = []
        summary.append("# Fusion 360 AI Training - Learning Summary\n")
        summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Add resume briefing
        summary.append(self.get_resume_briefing())
        summary.append("\n")
        
        # Add detailed session analysis
        summary.append("## Detailed Session History\n")
        
        if self.sessions_dir.exists():
            for session_dir in sorted(self.sessions_dir.iterdir()):
                if not session_dir.is_dir():
                    continue
                
                summary.append(f"\n### Session: {session_dir.name}\n")
                
                session_files = list(session_dir.glob("*_session.json"))
                if not session_files:
                    continue
                
                for session_file in session_files:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    task = data['task']
                    feedback = data['analysis']['feedback']
                    
                    summary.append(f"\n#### {task['task_id']}\n")
                    summary.append(f"- **Description:** {task['description']}\n")
                    summary.append(f"- **Score:** {feedback['overall_score']:.1f}/100\n")
                    
                    if feedback.get('issues'):
                        summary.append("- **Issues:**\n")
                        for issue in feedback['issues'][:3]:  # Top 3 issues
                            summary.append(f"  - {issue}\n")
                    
                    if feedback.get('suggestions'):
                        summary.append("- **Key Learnings:**\n")
                        for suggestion in feedback['suggestions'][:3]:  # Top 3 suggestions
                            summary.append(f"  - {suggestion}\n")
        
        summary_text = "".join(summary)
        
        with open(output_file, 'w') as f:
            f.write(summary_text)
        
        return summary_text


if __name__ == '__main__':
    import sys
    
    workspace = Path(__file__).parent
    manager = SessionManager(workspace)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        # Export learning summary
        summary = manager.export_learning_summary()
        print("Learning summary exported to training_data/learning_summary.md")
    else:
        # Print resume briefing
        briefing = manager.get_resume_briefing()
        print(briefing)

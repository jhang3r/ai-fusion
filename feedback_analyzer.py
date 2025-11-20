"""
Feedback Analyzer for Fusion 360 AI Training System
Analyzes exported models and provides detailed feedback for improvement.
"""

import numpy as np
import trimesh
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json


class MeshAnalyzer:
    """Analyzes 3D mesh quality and characteristics"""
    
    def __init__(self, mesh_path: Path):
        """Load and prepare mesh for analysis"""
        self.mesh_path = mesh_path
        self.mesh = trimesh.load(str(mesh_path))
        
    def analyze(self) -> Dict:
        """Perform comprehensive mesh analysis"""
        return {
            'basic_stats': self.get_basic_stats(),
            'quality_metrics': self.get_quality_metrics(),
            'geometric_properties': self.get_geometric_properties(),
            'topology_analysis': self.get_topology_analysis()
        }
    
    def get_basic_stats(self) -> Dict:
        """Get basic mesh statistics"""
        return {
            'vertex_count': len(self.mesh.vertices),
            'face_count': len(self.mesh.faces),
            'edge_count': len(self.mesh.edges),
            'is_watertight': self.mesh.is_watertight,
            'is_manifold': self.mesh.is_winding_consistent
        }
    
    def get_quality_metrics(self) -> Dict:
        """Calculate mesh quality metrics"""
        # Face areas
        face_areas = self.mesh.area_faces
        
        # Edge lengths
        edge_lengths = np.linalg.norm(
            self.mesh.vertices[self.mesh.edges[:, 0]] - 
            self.mesh.vertices[self.mesh.edges[:, 1]], 
            axis=1
        )
        
        # Face angles
        face_angles = self.mesh.face_angles
        
        return {
            'min_face_area': float(np.min(face_areas)),
            'max_face_area': float(np.max(face_areas)),
            'avg_face_area': float(np.mean(face_areas)),
            'min_edge_length': float(np.min(edge_lengths)),
            'max_edge_length': float(np.max(edge_lengths)),
            'avg_edge_length': float(np.mean(edge_lengths)),
            'min_face_angle_deg': float(np.min(np.degrees(face_angles))),
            'max_face_angle_deg': float(np.max(np.degrees(face_angles))),
            'aspect_ratio_score': self._calculate_aspect_ratio_score(face_areas, edge_lengths)
        }
    
    def get_geometric_properties(self) -> Dict:
        """Calculate geometric properties"""
        bounds = self.mesh.bounds
        extents = self.mesh.extents
        
        return {
            'volume_cm3': float(self.mesh.volume),
            'surface_area_cm2': float(self.mesh.area),
            'bounding_box': {
                'min': bounds[0].tolist(),
                'max': bounds[1].tolist(),
                'extents': extents.tolist()
            },
            'center_of_mass': self.mesh.center_mass.tolist(),
            'inertia_tensor': self.mesh.moment_inertia.tolist()
        }
    
    def get_topology_analysis(self) -> Dict:
        """Analyze mesh topology"""
        # Euler characteristic (should be 2 for a closed surface)
        euler_char = len(self.mesh.vertices) - len(self.mesh.edges) + len(self.mesh.faces)
        
        # Check for degenerate faces
        degenerate_faces = np.sum(self.mesh.area_faces < 1e-10)
        
        return {
            'euler_characteristic': int(euler_char),
            'is_closed_surface': euler_char == 2,
            'degenerate_face_count': int(degenerate_faces),
            'connected_components': len(self.mesh.split()),
            'genus': (2 - euler_char) // 2  # For closed surfaces
        }
    
    def _calculate_aspect_ratio_score(self, face_areas, edge_lengths) -> float:
        """Calculate overall mesh quality based on aspect ratios (0-100)"""
        # Higher is better - penalize extreme variations
        area_variation = np.std(face_areas) / (np.mean(face_areas) + 1e-10)
        edge_variation = np.std(edge_lengths) / (np.mean(edge_lengths) + 1e-10)
        
        # Convert to 0-100 score (lower variation = higher score)
        score = 100 / (1 + area_variation + edge_variation)
        return float(score)


class DimensionalComparator:
    """Compare dimensions against specifications"""
    
    def __init__(self, mesh: trimesh.Trimesh, target_dims: Dict):
        self.mesh = mesh
        self.target_dims = target_dims
    
    def compare(self) -> Dict:
        """Compare actual dimensions to target specifications"""
        results = {
            'dimensions': {},
            'accuracy_score': 0.0,
            'deviations': {}
        }
        
        actual_extents = self.mesh.extents
        
        # Compare each dimension
        dim_names = ['x', 'y', 'z']
        deviations = []
        
        for i, dim_name in enumerate(dim_names):
            if dim_name in self.target_dims:
                target = self.target_dims[dim_name]
                actual = actual_extents[i]
                deviation = abs(actual - target) / target * 100
                
                results['dimensions'][dim_name] = {
                    'target': target,
                    'actual': float(actual),
                    'deviation_percent': float(deviation)
                }
                deviations.append(deviation)
        
        # Calculate overall accuracy score (0-100)
        if deviations:
            avg_deviation = np.mean(deviations)
            results['accuracy_score'] = float(max(0, 100 - avg_deviation))
        
        # Check volume if specified
        if 'volume' in self.target_dims:
            target_vol = self.target_dims['volume']
            actual_vol = self.mesh.volume
            vol_deviation = abs(actual_vol - target_vol) / target_vol * 100
            
            results['dimensions']['volume'] = {
                'target': target_vol,
                'actual': float(actual_vol),
                'deviation_percent': float(vol_deviation)
            }
        
        return results


class FeedbackGenerator:
    """Generate actionable feedback based on analysis results"""
    
    def __init__(self, analysis: Dict, comparison: Optional[Dict] = None):
        self.analysis = analysis
        self.comparison = comparison
    
    def generate_feedback(self) -> Dict:
        """Generate comprehensive feedback"""
        feedback = {
            'overall_score': 0.0,
            'strengths': [],
            'issues': [],
            'suggestions': [],
            'detailed_metrics': {}
        }
        
        scores = []
        
        # Analyze basic quality
        basic_score, basic_feedback = self._analyze_basic_quality()
        scores.append(basic_score)
        feedback['strengths'].extend(basic_feedback['strengths'])
        feedback['issues'].extend(basic_feedback['issues'])
        feedback['suggestions'].extend(basic_feedback['suggestions'])
        
        # Analyze mesh quality
        quality_score, quality_feedback = self._analyze_mesh_quality()
        scores.append(quality_score)
        feedback['strengths'].extend(quality_feedback['strengths'])
        feedback['issues'].extend(quality_feedback['issues'])
        feedback['suggestions'].extend(quality_feedback['suggestions'])
        
        # Analyze dimensional accuracy if comparison provided
        if self.comparison:
            dim_score, dim_feedback = self._analyze_dimensional_accuracy()
            scores.append(dim_score)
            feedback['strengths'].extend(dim_feedback['strengths'])
            feedback['issues'].extend(dim_feedback['issues'])
            feedback['suggestions'].extend(dim_feedback['suggestions'])
        
        # Calculate overall score with weighted average
        # Dimensional accuracy is most important for functional parts
        if self.comparison:
            # Weight: 60% dimensions, 30% basic quality, 10% mesh quality
            feedback['overall_score'] = float(
                0.6 * dim_score + 0.3 * basic_score + 0.1 * quality_score
            )
        else:
            # No dimensions to compare - equal weight
            feedback['overall_score'] = float(np.mean(scores))
        
        # Add detailed metrics
        feedback['detailed_metrics'] = {
            'basic_quality_score': basic_score,
            'mesh_quality_score': quality_score,
            'dimensional_accuracy_score': dim_score if self.comparison else None
        }
        
        return feedback
    
    def _analyze_basic_quality(self) -> Tuple[float, Dict]:
        """Analyze basic mesh quality"""
        stats = self.analysis['basic_stats']
        feedback = {'strengths': [], 'issues': [], 'suggestions': []}
        score = 100.0
        
        # Check if watertight
        if stats['is_watertight']:
            feedback['strengths'].append("✓ Mesh is watertight (no holes)")
        else:
            feedback['issues'].append("✗ Mesh has holes - not watertight")
            feedback['suggestions'].append("Ensure all sketches are closed profiles before extruding")
            score -= 30
        
        # Check if manifold
        if stats['is_manifold']:
            feedback['strengths'].append("✓ Mesh has consistent winding (manifold)")
        else:
            feedback['issues'].append("✗ Mesh has inconsistent face normals")
            feedback['suggestions'].append("Check for overlapping geometry or reversed faces")
            score -= 20
        
        # Check vertex/face count (reasonable complexity)
        if 100 < stats['vertex_count'] < 100000:
            feedback['strengths'].append(f"✓ Good vertex count: {stats['vertex_count']}")
        elif stats['vertex_count'] <= 100:
            feedback['issues'].append(f"✗ Very low vertex count: {stats['vertex_count']}")
            feedback['suggestions'].append("Model may be too simple - add more detail")
            score -= 15
        else:
            feedback['issues'].append(f"✗ Very high vertex count: {stats['vertex_count']}")
            feedback['suggestions'].append("Model may be over-detailed - optimize mesh")
            score -= 10
        
        return max(0, score), feedback
    
    def _analyze_mesh_quality(self) -> Tuple[float, Dict]:
        """Analyze mesh quality metrics"""
        quality = self.analysis['quality_metrics']
        feedback = {'strengths': [], 'issues': [], 'suggestions': []}
        score = quality['aspect_ratio_score']
        
        # Check for degenerate faces
        topo = self.analysis['topology_analysis']
        if topo['degenerate_face_count'] == 0:
            feedback['strengths'].append("✓ No degenerate faces")
        else:
            feedback['issues'].append(f"✗ Found {topo['degenerate_face_count']} degenerate faces")
            feedback['suggestions'].append("Remove zero-area faces - may cause export issues")
            score -= 10
        
        # Check edge length consistency
        edge_ratio = quality['max_edge_length'] / (quality['min_edge_length'] + 1e-10)
        if edge_ratio < 100:
            feedback['strengths'].append("✓ Consistent edge lengths")
        else:
            feedback['issues'].append(f"✗ Large edge length variation (ratio: {edge_ratio:.1f})")
            feedback['suggestions'].append("Use more uniform mesh refinement settings")
            score -= 5  # Reduced from -15 (cosmetic issue)
        
        # Check face angles
        if quality['min_face_angle_deg'] > 10:
            feedback['strengths'].append("✓ No extremely acute angles")
        else:
            feedback['issues'].append(f"✗ Very acute angles found: {quality['min_face_angle_deg']:.1f}°")
            feedback['suggestions'].append("Avoid sharp corners - use fillets or chamfers")
            score -= 3  # Reduced from -10 (cosmetic issue)
        
        return max(0, score), feedback
    
    def _analyze_dimensional_accuracy(self) -> Tuple[float, Dict]:
        """Analyze dimensional accuracy against targets"""
        feedback = {'strengths': [], 'issues': [], 'suggestions': []}
        score = self.comparison['accuracy_score']
        
        # Check each dimension
        for dim_name, dim_data in self.comparison['dimensions'].items():
            deviation = dim_data['deviation_percent']
            
            if deviation < 1:
                feedback['strengths'].append(
                    f"✓ {dim_name.upper()}: {dim_data['actual']:.2f} "
                    f"(target: {dim_data['target']:.2f}, deviation: {deviation:.2f}%)"
                )
            elif deviation < 5:
                feedback['issues'].append(
                    f"⚠ {dim_name.upper()}: {dim_data['actual']:.2f} "
                    f"(target: {dim_data['target']:.2f}, deviation: {deviation:.2f}%)"
                )
                feedback['suggestions'].append(
                    f"Adjust {dim_name} dimension - currently off by {deviation:.2f}%"
                )
            else:
                feedback['issues'].append(
                    f"✗ {dim_name.upper()}: {dim_data['actual']:.2f} "
                    f"(target: {dim_data['target']:.2f}, deviation: {deviation:.2f}%)"
                )
                feedback['suggestions'].append(
                    f"CRITICAL: {dim_name} dimension is significantly wrong - check sketch constraints"
                )
        
        return score, feedback


def analyze_model(mesh_path: Path, target_dims: Optional[Dict] = None) -> Dict:
    """
    Main entry point for model analysis
    
    Args:
        mesh_path: Path to STL file
        target_dims: Optional dict with target dimensions {'x': 10, 'y': 20, 'z': 5, 'volume': 1000}
    
    Returns:
        Complete analysis and feedback
    """
    # Analyze mesh
    analyzer = MeshAnalyzer(mesh_path)
    analysis = analyzer.analyze()
    
    # Compare dimensions if targets provided
    comparison = None
    if target_dims:
        comparator = DimensionalComparator(analyzer.mesh, target_dims)
        comparison = comparator.compare()
    
    # Generate feedback
    feedback_gen = FeedbackGenerator(analysis, comparison)
    feedback = feedback_gen.generate_feedback()
    
    return {
        'analysis': analysis,
        'comparison': comparison,
        'feedback': feedback
    }


if __name__ == '__main__':
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python feedback_analyzer.py <stl_file> [target_x] [target_y] [target_z]")
        sys.exit(1)
    
    mesh_path = Path(sys.argv[1])
    
    target_dims = None
    if len(sys.argv) >= 5:
        target_dims = {
            'x': float(sys.argv[2]),
            'y': float(sys.argv[3]),
            'z': float(sys.argv[4])
        }
    
    result = analyze_model(mesh_path, target_dims)
    
    print("\n" + "="*60)
    print("MESH ANALYSIS REPORT")
    print("="*60)
    print(f"\nFile: {mesh_path.name}")
    print(f"Overall Score: {result['feedback']['overall_score']:.1f}/100")
    
    print("\n--- STRENGTHS ---")
    for strength in result['feedback']['strengths']:
        print(f"  {strength}")
    
    print("\n--- ISSUES ---")
    for issue in result['feedback']['issues']:
        print(f"  {issue}")
    
    print("\n--- SUGGESTIONS ---")
    for suggestion in result['feedback']['suggestions']:
        print(f"  • {suggestion}")
    
    print("\n" + "="*60)

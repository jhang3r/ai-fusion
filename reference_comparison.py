"""
Reference Comparison System
Compares generated models against reference images and models for visual/geometric similarity.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
import trimesh
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json


class ImageComparator:
    """Compare rendered images for visual similarity"""
    
    def __init__(self, reference_image_path: Path, generated_image_path: Path):
        self.reference = Image.open(reference_image_path).convert('RGB')
        self.generated = Image.open(generated_image_path).convert('RGB')
        
        # Ensure same size for comparison
        if self.reference.size != self.generated.size:
            self.generated = self.generated.resize(self.reference.size, Image.Resampling.LANCZOS)
    
    def compare(self) -> Dict:
        """Perform comprehensive image comparison"""
        return {
            'pixel_similarity': self._pixel_similarity(),
            'structural_similarity': self._structural_similarity(),
            'color_distribution': self._color_distribution_similarity(),
            'edge_similarity': self._edge_similarity(),
            'overall_score': 0.0  # Calculated as weighted average
        }
    
    def _pixel_similarity(self) -> float:
        """Calculate pixel-wise similarity (0-100)"""
        # Convert to numpy arrays
        ref_array = np.array(self.reference, dtype=np.float32)
        gen_array = np.array(self.generated, dtype=np.float32)
        
        # Calculate mean squared error
        mse = np.mean((ref_array - gen_array) ** 2)
        
        # Convert to similarity score (0-100)
        # MSE of 0 = perfect match (100), higher MSE = lower score
        max_mse = 255 ** 2  # Maximum possible MSE for 8-bit images
        similarity = 100 * (1 - min(mse / max_mse, 1.0))
        
        return float(similarity)
    
    def _structural_similarity(self) -> float:
        """Calculate structural similarity using simple method"""
        # Convert to grayscale
        ref_gray = np.array(self.reference.convert('L'), dtype=np.float32)
        gen_gray = np.array(self.generated.convert('L'), dtype=np.float32)
        
        # Calculate means and standard deviations
        ref_mean = np.mean(ref_gray)
        gen_mean = np.mean(gen_gray)
        ref_std = np.std(ref_gray)
        gen_std = np.std(gen_gray)
        
        # Calculate correlation
        covariance = np.mean((ref_gray - ref_mean) * (gen_gray - gen_mean))
        
        # Simplified SSIM-like score
        c1 = (0.01 * 255) ** 2
        c2 = (0.03 * 255) ** 2
        
        luminance = (2 * ref_mean * gen_mean + c1) / (ref_mean**2 + gen_mean**2 + c1)
        contrast = (2 * ref_std * gen_std + c2) / (ref_std**2 + gen_std**2 + c2)
        
        similarity = luminance * contrast * 100
        
        return float(np.clip(similarity, 0, 100))
    
    def _color_distribution_similarity(self) -> float:
        """Compare color histograms"""
        # Get histograms for each channel
        ref_hist = self.reference.histogram()
        gen_hist = self.generated.histogram()
        
        # Calculate histogram intersection (normalized)
        intersection = sum(min(a, b) for a, b in zip(ref_hist, gen_hist))
        total = sum(ref_hist)
        
        similarity = 100 * (intersection / total)
        
        return float(similarity)
    
    def _edge_similarity(self) -> float:
        """Compare edge detection results"""
        from PIL import ImageFilter
        
        # Apply edge detection
        ref_edges = self.reference.convert('L').filter(ImageFilter.FIND_EDGES)
        gen_edges = self.generated.convert('L').filter(ImageFilter.FIND_EDGES)
        
        # Convert to arrays
        ref_array = np.array(ref_edges, dtype=np.float32)
        gen_array = np.array(gen_edges, dtype=np.float32)
        
        # Calculate similarity
        mse = np.mean((ref_array - gen_array) ** 2)
        max_mse = 255 ** 2
        similarity = 100 * (1 - min(mse / max_mse, 1.0))
        
        return float(similarity)
    
    def generate_comparison_image(self, output_path: Path) -> Path:
        """Generate side-by-side comparison image with difference map"""
        # Create comparison layout
        width = self.reference.width
        height = self.reference.height
        
        # Create canvas (3 images side by side + labels)
        canvas = Image.new('RGB', (width * 3, height + 40), 'white')
        
        # Add reference image
        canvas.paste(self.reference, (0, 40))
        
        # Add generated image
        canvas.paste(self.generated, (width, 40))
        
        # Create difference map
        diff = ImageChops.difference(self.reference, self.generated)
        # Enhance difference for visibility
        diff = diff.point(lambda p: p * 3)
        canvas.paste(diff, (width * 2, 40))
        
        # Add labels
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((width // 2 - 50, 10), "Reference", fill='black', font=font)
        draw.text((width + width // 2 - 50, 10), "Generated", fill='black', font=font)
        draw.text((width * 2 + width // 2 - 50, 10), "Difference", fill='black', font=font)
        
        # Save
        canvas.save(output_path)
        return output_path


class ModelComparator:
    """Compare 3D models for geometric similarity"""
    
    def __init__(self, reference_mesh_path: Path, generated_mesh_path: Path):
        self.reference = trimesh.load(str(reference_mesh_path))
        self.generated = trimesh.load(str(generated_mesh_path))
    
    def compare(self) -> Dict:
        """Perform comprehensive model comparison"""
        # Align meshes for fair comparison
        self._align_meshes()
        
        return {
            'volume_similarity': self._volume_similarity(),
            'surface_area_similarity': self._surface_area_similarity(),
            'shape_similarity': self._shape_similarity(),
            'vertex_density_similarity': self._vertex_density_similarity(),
            'overall_score': 0.0  # Calculated as weighted average
        }
    
    def _align_meshes(self):
        """Align meshes to same coordinate system"""
        # Center both meshes
        self.reference.vertices -= self.reference.center_mass
        self.generated.vertices -= self.generated.center_mass
        
        # Scale to same bounding box size (optional)
        ref_scale = np.max(self.reference.extents)
        gen_scale = np.max(self.generated.extents)
        if gen_scale > 0:
            self.generated.vertices *= (ref_scale / gen_scale)
    
    def _volume_similarity(self) -> float:
        """Compare volumes"""
        ref_vol = abs(self.reference.volume)
        gen_vol = abs(self.generated.volume)
        
        if ref_vol == 0:
            return 100.0 if gen_vol == 0 else 0.0
        
        ratio = min(ref_vol, gen_vol) / max(ref_vol, gen_vol)
        return float(ratio * 100)
    
    def _surface_area_similarity(self) -> float:
        """Compare surface areas"""
        ref_area = self.reference.area
        gen_area = self.generated.area
        
        if ref_area == 0:
            return 100.0 if gen_area == 0 else 0.0
        
        ratio = min(ref_area, gen_area) / max(ref_area, gen_area)
        return float(ratio * 100)
    
    def _shape_similarity(self) -> float:
        """Compare overall shape using bounding box and moments"""
        # Compare bounding box extents
        ref_extents = self.reference.extents
        gen_extents = self.generated.extents
        
        extent_ratios = []
        for ref_e, gen_e in zip(ref_extents, gen_extents):
            if max(ref_e, gen_e) > 0:
                ratio = min(ref_e, gen_e) / max(ref_e, gen_e)
                extent_ratios.append(ratio)
        
        if not extent_ratios:
            return 0.0
        
        return float(np.mean(extent_ratios) * 100)
    
    def _vertex_density_similarity(self) -> float:
        """Compare vertex density (vertices per unit volume)"""
        ref_density = len(self.reference.vertices) / max(abs(self.reference.volume), 1e-10)
        gen_density = len(self.generated.vertices) / max(abs(self.generated.volume), 1e-10)
        
        ratio = min(ref_density, gen_density) / max(ref_density, gen_density)
        return float(ratio * 100)
    
    def calculate_hausdorff_distance(self) -> float:
        """Calculate Hausdorff distance between meshes (expensive but accurate)"""
        # Sample points on both surfaces
        ref_points = self.reference.sample(1000)
        gen_points = self.generated.sample(1000)
        
        # Calculate one-way distances
        from scipy.spatial.distance import cdist
        
        distances_ref_to_gen = cdist(ref_points, gen_points)
        distances_gen_to_ref = cdist(gen_points, ref_points)
        
        # Hausdorff distance
        hausdorff = max(
            np.max(np.min(distances_ref_to_gen, axis=1)),
            np.max(np.min(distances_gen_to_ref, axis=1))
        )
        
        return float(hausdorff)


class ReferenceManager:
    """Manage reference images and models for comparison"""
    
    def __init__(self, references_dir: Path):
        self.references_dir = references_dir
        self.models_dir = references_dir / "models"
        self.images_dir = references_dir / "images"
        
        # Ensure directories exist
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self.catalog = self._load_catalog()
    
    def _load_catalog(self) -> Dict:
        """Load reference catalog"""
        catalog_file = self.references_dir / "catalog.json"
        
        if catalog_file.exists():
            with open(catalog_file, 'r') as f:
                return json.load(f)
        
        return {'models': {}, 'images': {}}
    
    def _save_catalog(self):
        """Save reference catalog"""
        catalog_file = self.references_dir / "catalog.json"
        
        with open(catalog_file, 'w') as f:
            json.dump(self.catalog, f, indent=2)
    
    def add_reference_model(self, name: str, model_path: Path, metadata: Optional[Dict] = None):
        """Add a reference model to the catalog"""
        # Copy model to references directory
        dest_path = self.models_dir / model_path.name
        
        import shutil
        shutil.copy(model_path, dest_path)
        
        self.catalog['models'][name] = {
            'path': str(dest_path.relative_to(self.references_dir)),
            'metadata': metadata or {}
        }
        
        self._save_catalog()
    
    def add_reference_image(self, name: str, image_path: Path, metadata: Optional[Dict] = None):
        """Add a reference image to the catalog"""
        # Copy image to references directory
        dest_path = self.images_dir / image_path.name
        
        import shutil
        shutil.copy(image_path, dest_path)
        
        self.catalog['images'][name] = {
            'path': str(dest_path.relative_to(self.references_dir)),
            'metadata': metadata or {}
        }
        
        self._save_catalog()
    
    def get_reference_model(self, name: str) -> Optional[Path]:
        """Get path to reference model"""
        if name in self.catalog['models']:
            rel_path = self.catalog['models'][name]['path']
            return self.references_dir / rel_path
        return None
    
    def get_reference_image(self, name: str) -> Optional[Path]:
        """Get path to reference image"""
        if name in self.catalog['images']:
            rel_path = self.catalog['images'][name]['path']
            return self.references_dir / rel_path
        return None
    
    def list_references(self) -> Dict:
        """List all available references"""
        return {
            'models': list(self.catalog['models'].keys()),
            'images': list(self.catalog['images'].keys())
        }


def compare_with_reference(generated_model: Path, 
                          reference_name: str,
                          references_dir: Path,
                          output_dir: Optional[Path] = None) -> Dict:
    """
    Main entry point for reference comparison
    
    Args:
        generated_model: Path to generated STL file
        reference_name: Name of reference in catalog
        references_dir: Path to references directory
        output_dir: Optional output directory for comparison images
    
    Returns:
        Comparison results with scores
    """
    manager = ReferenceManager(references_dir)
    
    # Get reference model
    reference_model = manager.get_reference_model(reference_name)
    
    if reference_model is None:
        return {
            'error': f'Reference model "{reference_name}" not found',
            'available_references': manager.list_references()
        }
    
    # Compare models
    model_comparator = ModelComparator(reference_model, generated_model)
    model_comparison = model_comparator.compare()
    
    # Calculate overall model score
    weights = {
        'volume_similarity': 0.3,
        'surface_area_similarity': 0.2,
        'shape_similarity': 0.4,
        'vertex_density_similarity': 0.1
    }
    
    model_comparison['overall_score'] = sum(
        model_comparison[key] * weight 
        for key, weight in weights.items()
    )
    
    return {
        'reference_name': reference_name,
        'model_comparison': model_comparison,
        'generated_model': str(generated_model),
        'reference_model': str(reference_model)
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python reference_comparison.py <generated_model> <reference_name> <references_dir>")
        sys.exit(1)
    
    generated = Path(sys.argv[1])
    reference_name = sys.argv[2]
    references_dir = Path(sys.argv[3])
    
    result = compare_with_reference(generated, reference_name, references_dir)
    
    print("\n" + "="*60)
    print("REFERENCE COMPARISON REPORT")
    print("="*60)
    
    if 'error' in result:
        print(f"\n❌ Error: {result['error']}")
        print("\nAvailable references:")
        for ref_type, refs in result['available_references'].items():
            print(f"  {ref_type}: {', '.join(refs)}")
    else:
        print(f"\nReference: {result['reference_name']}")
        print(f"Overall Score: {result['model_comparison']['overall_score']:.1f}/100")
        print("\nDetailed Scores:")
        for key, value in result['model_comparison'].items():
            if key != 'overall_score':
                print(f"  {key}: {value:.1f}/100")
    
    print("\n" + "="*60)

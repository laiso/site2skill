
import os
import shutil
import unittest
import tempfile
from site2skill.utils import sanitize_path
from site2skill.generate_skill_structure import generate_skill_structure

class TestSite2Skill(unittest.TestCase):
    def test_sanitize_path(self):
        """Test the sanitize_path utility function."""
        # Standard cases
        self.assertEqual(sanitize_path("docs.example.com/api/index.md"), 'docs.example.com/api/index.md')
        self.assertEqual(sanitize_path("docs@example.com/api#v1/index.md"), 'docs_example.com/api_v1/index.md')
        
        # Edge cases
        self.assertEqual(sanitize_path(""), 'file.md')
        self.assertEqual(sanitize_path("   "), '___') # Spaces are replaced or handled
        self.assertEqual(sanitize_path("/absolute/path"), 'absolute/path') # Leading slash is removed

    def test_generate_skill_structure(self):
        """Test the generate_skill_structure function."""
        # Setup temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, "test_src")
        self.output_base = os.path.join(self.test_dir, "test_output")
        
        os.makedirs(self.source_dir)
        
        try:
            # Create test files in source directory
            with open(os.path.join(self.source_dir, "root.md"), "w") as f:
                f.write("# Root")
            
            sub_dir = os.path.join(self.source_dir, "sub")
            os.makedirs(sub_dir)
            with open(os.path.join(sub_dir, "nested.md"), "w") as f:
                f.write("# Nested")
                
            # Run generator
            skill_name = "test_skill"
            generate_skill_structure(skill_name, self.source_dir, self.output_base)
            
            # Verify structure
            skill_dir = os.path.join(self.output_base, skill_name)
            self.assertTrue(os.path.exists(os.path.join(skill_dir, "SKILL.md")), "SKILL.md should be created")
            
            # Verify docs content
            docs_dir = os.path.join(skill_dir, "docs")
            self.assertTrue(os.path.exists(os.path.join(docs_dir, "root.md")), "root.md should be copied")
            self.assertTrue(os.path.exists(os.path.join(docs_dir, "sub", "nested.md")), "nested.md should be copied in subdir")
            
            # Verify scripts
            scripts_dir = os.path.join(skill_dir, "scripts")
            self.assertTrue(os.path.exists(os.path.join(scripts_dir, "search_docs.py")), "search_docs.py should be installed")
            self.assertTrue(os.path.exists(os.path.join(scripts_dir, "README.md")), "scripts/README.md should be installed")

        finally:
            # Cleanup
            shutil.rmtree(self.test_dir)

if __name__ == '__main__':
    unittest.main()

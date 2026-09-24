import json
import subprocess
import unittest
from pathlib import Path


class ViewerTests(unittest.TestCase):
    def test_artifact_parser_preserves_hashes_and_metrics_model(self):
        payload = {
            "audit": {"schema_version": "v1", "project": "TSUJI WORLD", "edition": "ED-000001", "release": "r1", "status": "passed", "stages": ["ingest", "proof"], "counts": {"fixity_checks": 2}, "fixity": {"masters": {"checked": 2, "failures": []}}},
            "proof": {"schema_version": "v1", "proof_sha256": "a" * 64, "records": [{"id": "TSJ-000001"}], "signoffs": {}},
            "signoff": {"schema_version": "v1", "proof_sha256": "a" * 64, "signoff_sha256": "b" * 64, "signoffs": {}},
            "routes": {"TSJ-000001": {"ja": "/works/tsj-000001"}},
        }
        script = "const v=require('./site/audit-viewer.js'); const x=JSON.parse(process.argv[1]); const m=v.buildViewModel(x); if(m.proofHash !== '" + "a" * 64 + "' || m.routeCount !== 1 || !m.fixityHealthy) process.exit(1); console.log(m.recordCount);"
        result = subprocess.run(["node", "-e", script, json.dumps(payload)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "1")

    def test_viewer_has_no_external_requests_or_private_paths(self):
        source = Path("site/audit-viewer.html").read_text()
        script = Path("site/audit-viewer.js").read_text()
        self.assertNotIn("fetch(", source + script)
        self.assertNotIn("archive/", source + script)
        self.assertNotIn("master/", source + script)
        self.assertNotIn("https://", source + script)


if __name__ == "__main__":
    unittest.main()
from utils.pipeline_runner import PipelineRunner
import sys

if __name__ == "__main__":
    case_cfg = sys.argv[1] if len(sys.argv) > 1 else "cases/case1/case.yaml"
    runner = PipelineRunner(case_cfg)
    runner.load_plugins()
    runner.run_all()

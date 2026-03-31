import json
import sys
from pathlib import Path

from tender_system.schemas import TenderRequest
from tender_system.service import TenderGenerationService, build_demo_request_payload


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

    base_dir = Path(__file__).resolve().parent
    service = TenderGenerationService(base_dir / "data" / "enterprise_docs.json")
    request = TenderRequest.model_validate(build_demo_request_payload())
    result = service.generate_tender(request)

    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "generated_tender.json"
    output_path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== 智能标书生成结果 ===")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    print(f"\n结果已写入: {output_path}")


if __name__ == "__main__":
    main()

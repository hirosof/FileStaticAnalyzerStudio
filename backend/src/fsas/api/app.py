from fastapi import Depends, FastAPI, HTTPException, UploadFile
from nanoid import generate
from sqlalchemy import select
from sqlalchemy.orm import Session

from fsas.api.deps import get_db
from fsas.api.schemas import EventOut, ItemStatusOut, SpecimenOut
from fsas.contracts import AnalysisJob
from fsas.models import AnalysisRequest, AnalysisRequestItem, JobEvent, SpecimenInformation
from fsas.queue import enqueue
from fsas.storage import storage

app = FastAPI(title="FileStaticAnalyzerStudio API")


@app.post("/submit")
async def submit(file: UploadFile, db: Session = Depends(get_db)):
    reception_id = generate()
    item_id = generate()

    # 1) DB 行を先に作成・コミット（Worker が読む時に必ず存在するように）
    db.add(AnalysisRequest(request_reception_id=reception_id))
    db.add(
        AnalysisRequestItem(
            request_item_id=item_id,
            request_reception_id=reception_id,
            original_name=file.filename,
            process_state="Pending",
        )
    )
    db.commit()

    # 2) 実体をステージング保存
    storage.stage(item_id, file.file)

    # 3) ジョブを Stream へ投入
    enqueue(AnalysisJob(request_item_id=item_id))

    # 4) nanoid を即返却（解析は Worker が非同期で行う）
    return {"request_reception_id": reception_id, "request_item_id": item_id}


@app.get("/items/{request_item_id}", response_model=ItemStatusOut)
def get_item(request_item_id: str, db: Session = Depends(get_db)):
    item = db.scalar(
        select(AnalysisRequestItem).where(
            AnalysisRequestItem.request_item_id == request_item_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")

    specimen = None
    if item.sha256:
        spec = db.scalar(
            select(SpecimenInformation).where(SpecimenInformation.sha256 == item.sha256)
        )
        if spec is not None:
            specimen = SpecimenOut.model_validate(spec)

    return ItemStatusOut(
        request_item_id=item.request_item_id,
        request_reception_id=item.request_reception_id,
        original_name=item.original_name,
        process_state=item.process_state,
        current_phase=item.current_phase,
        error_type=item.error_type,
        sha256=item.sha256,
        specimen=specimen,
    )


@app.get("/items/{request_item_id}/events", response_model=list[EventOut])
def get_item_events(request_item_id: str, db: Session = Depends(get_db)):
    events = db.scalars(
        select(JobEvent)
        .where(JobEvent.request_item_id == request_item_id)
        .order_by(JobEvent.id)
    ).all()
    return list(events)
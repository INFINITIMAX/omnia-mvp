import hashlib
import importlib
import json
from pathlib import Path

import pytest

TEXT = "1.1.\nText sintetic pentru inlocuire pending."
META = {"document_id":"pending_1","cod_oficial":"NP 001-2026","titlu_oficial":"Normativ sintetic","an":2026}

@pytest.fixture
def module(): return importlib.import_module("replace_pending_ingestion")

@pytest.fixture
def inputs(tmp_path, module, monkeypatch):
    inbox=tmp_path/"documente_noi"/"_inbox"; reports=tmp_path/"documente_noi"/"_reports"
    inbox.mkdir(parents=True); reports.mkdir()
    monkeypatch.setattr(module.base,"FOLDER_INBOX",inbox); monkeypatch.setattr(module.base,"FOLDER_RAPOARTE",reports)
    pdf=inbox/"doc.pdf"; pdf.write_bytes(b"pdf")
    sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
    report=reports/"r.json"; report.write_text(json.dumps({"status":"ready_for_human_metadata","source_sha256":sha,"page_count":1,"character_count":len(TEXT),"chunk_count":2,"metadata_candidates":{"cod_oficial":META["cod_oficial"],"titlu_oficial":META["titlu_oficial"],"an":2026}}))
    metadata=reports/"m.json"; metadata.write_text(json.dumps(META))
    return pdf,report,metadata

def chunks(_): return [{"articol":"1.1","text":TEXT[:20]},{"articol":"1.2","text":TEXT[20:]}]
def extract(_): return TEXT,1

class Cursor:
    def __init__(self,status="indexed_pending_validation",delete_count=2,insert_counts=None): self.status=status; self.delete_count=delete_count; self.insert_counts=iter(insert_counts or [1,1]); self.calls=[]; self.rowcount=0; self.last=""; self.closed=False
    def execute(self,sql,params=None):
        self.calls.append((sql,params)); self.last=sql
        if "DELETE" in sql: self.rowcount=self.delete_count
        elif "INSERT INTO public.documente_chunks" in sql: self.rowcount=next(self.insert_counts)
        else: self.rowcount=1
    def fetchall(self): return [("pending_1","pdf_x","NP 001-2026",self.status)] if "SELECT document_id" in self.last else []
    def close(self): self.closed=True
class Conn:
    def __init__(self,c,commit_error=False): self.c=c; self.commit_error=commit_error; self.commits=0; self.rollbacks=0; self.closed=False
    def cursor(self): return self.c
    def commit(self):
        self.commits+=1
        if self.commit_error: raise RuntimeError()
    def rollback(self): self.rollbacks+=1
    def close(self): self.closed=True
class Voyage:
    def __init__(self, events): self.events=events
    def count_tokens(self,texts,model=None): self.events.append("tokens"); return 5
    def embed(self,texts,model=None,input_type=None): self.events.append("embed"); return type("R",(),{"embeddings":[[.1] for _ in texts]})()

def call(m,ins,commit=False,**kw):
    return m.replace_pending_document(*ins,commit=commit,extract_pdf=extract,create_chunks=chunks,**kw)

def test_dry_run_no_db_or_voyage(module,inputs):
    assert call(module,inputs,connection_factory=lambda:pytest.fail("db"),voyage_client_factory=lambda:pytest.fail("voyage"))["status"]=="validated"

def test_commit_verifica_pending_sub_lock_inainte_de_voyage_si_delete(module,inputs):
    events=[]; c=Cursor(); conn=Conn(c)
    assert call(module,inputs,True,connection_factory=lambda:conn,voyage_client_factory=lambda:Voyage(events))["status"]=="indexed_pending_validation"
    select_index=next(i for i,x in enumerate(c.calls) if "SELECT document_id" in x[0])
    delete_index=next(i for i,x in enumerate(c.calls) if "DELETE" in x[0])
    delete= c.calls[delete_index]
    assert delete[1]==("pending_1",) and select_index < delete_index and events.index("embed") < delete_index
    assert conn.commits==1 and conn.rollbacks==0

@pytest.mark.parametrize("status,delete_count,token,expects_voyage",[("approved",2,"pending_identity_mismatch",False),("indexed_pending_validation",0,"no_existing_chunks",True)])
def test_commit_refuses_nonpending_or_missing_chunks_with_rollback(module,inputs,status,delete_count,token,expects_voyage):
    events=[]; conn=Conn(Cursor(status,delete_count))
    with pytest.raises(module.base.ImportError,match=token): call(module,inputs,True,connection_factory=lambda:conn,voyage_client_factory=lambda:Voyage(events))
    assert bool(events) is expects_voyage and conn.rollbacks==1

def test_commit_checks_every_insert_and_commit_unknown_no_rollback(module,inputs):
    conn=Conn(Cursor(insert_counts=[1,0]))
    with pytest.raises(module.base.ImportError,match="insert_cardinality"): call(module,inputs,True,connection_factory=lambda:conn,voyage_client_factory=lambda:Voyage([]))
    assert conn.rollbacks==1
    conn=Conn(Cursor(),True)
    with pytest.raises(module.base.ImportError,match="commit_unknown"): call(module,inputs,True,connection_factory=lambda:conn,voyage_client_factory=lambda:Voyage([]))
    assert conn.commits==1 and conn.rollbacks==0

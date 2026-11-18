import re, json, collections
O='/mnt/user-data/outputs/'
F={'PRD':'PRD_v0_3.md','SEC':'security-v0_4.md','SD':'SYSTEM_DESIGN_v1_2.md','RP':'lotline_research_prompt_v3_1.md'}
T={k:open(O+v,encoding='utf-8').read() for k,v in F.items()}
out=[]
def P(*a): out.append(' '.join(str(x) for x in a)); print(*a)
# 1 reason codes
canon=['HOLD_PLAN_MISSING','HOLD_PLAN_INVALID','REJECT_CRITICAL_NONVISUAL_FAILED','REJECT_LIMIT_REACHED','ESCALATE_CRITICAL_UNREVIEWED','ESCALATE_UNMAPPED_CLAUSE','ESCALATE_CRITICAL_REJECTION_UNCONFIRMED','ESCALATE_SECOND_OPINION_REQUESTED','HOLD_UNITS_MISSING','HOLD_VIEWS_PENDING','HOLD_CRITICAL_NONVISUAL_PENDING','HOLD_VIEW_STATE_INCONSISTENT','HOLD_EVIDENCE_INTEGRITY','HOLD_COMPUTE_ERROR','ACCEPT_PLAN_MET']
P('== A. canonical reason codes present per document (count of mentions)')
for c in canon: P(' ',c.ljust(42),{k:T[k].count(c) for k in T})
codepat=re.compile(r'(?<![A-Za-z0-9_`])`?((?:HOLD|ESCALATE|REJECT|ACCEPT)_[A-Z_]+)`?')
P('== B. reason-like codes NOT in the canonical list (per document)')
for k in T:
    seen=collections.Counter(m for m in codepat.findall(T[k]) if m not in canon)
    P(' ',k,dict(seen))
# 2 retired names outside crosswalk/history
retired=['CLASS_RE_REACHED','ALL_CLASSES_WITHIN_AC','PLAN_N_MISMATCH','PLAN_CONFIG_ERROR','OVERRIDE_RELEASE','(?<![A-Z_])PLAN_MISSING(?![A-Z_])','(?<![A-Z_])UNREVIEWED(?![A-Z_])','(?<![A-Z_])NOT_INFERRED(?![A-Z_])']
P('== C. retired names (mentions per document; crosswalk/history rows are expected)')
for r in retired: P(' ',r.ljust(46),{k:len(re.findall(r,T[k])) for k in T})
# 3 stale filenames
P('== D. references to superseded filenames')
for fn in ['security-v0_3.md','security-v0.2.md','SYSTEM_DESIGN_v1_1.md','lotline_research_prompt_v3.md','lotline_architecture_prompt.md','PRD_v0.2.md','PRD__3_.md']:
    P(' ',fn.ljust(34),{k:T[k].count(fn) for k in T})
# 4 DB role names & table/function names per doc
P('== E. role, table and function names per document')
names=['lotline_owner','lotline_app','lotline_dispatcher','lotline_dispatch_writer','lotline_decision_writer','lotline_api_writer','lotline_model_writer','lotline_backup','inference_job','model_activation','model_selftest','v_image_inference_status','v_active_model','v_protected_trigger_check','next_attempt_at','dispatcher_claim_job','dispatcher_heartbeat','dispatcher_fail_job','dispatcher_record_predictions','dispatcher_claim_selftest','dispatcher_record_selftest','api_cancel_job','app_register_model','app_activate_model','record_decision','defect_class','counting_mode','critical_nonvisual_status','zone_code','size_band','InferenceWorker','inference-worker','`vision`']
for n in names: P(' ',n.ljust(32),{k:T[k].count(n) for k in T})
# 5 obsolete architecture terms
P('== F. obsolete-architecture patterns (expect 0 outside history/audit rows)')
pats={'api joined to infer_net':r'`api`[^\n|]{0,30}`app_net`, `db_net`, `infer_net`','API sends bytes to inference':r'API (sends|asks)[^\n]{0,60}(inference|detector)','`inference` container token':r'`inference`(?!-)','image inference_status column':r'inference_status\b(?!`)','PostgreSQL 17':r'PostgreSQL 17|postgres:17','per-class n':r'n, Ac, Re\)|`n`[^\n]{0,15}per class','Admin may override':r'(supervisor or admin|Supervisor or Admin)[^\n]{0,30}overrid','HOLD overridden':r'HOLD[^\n]{0,40}(may|can) be overridden','Supervisor+':r'Supervisor\+','is_active on model':r'model_version[^\n]{0,60}is_active'}
for n,p in pats.items(): P(' ',n.ljust(32),{k:len(re.findall(p,T[k])) for k in T})
# 6 cross-reference existence: PRD -> Security IDs
sec_ids=set(re.findall(r'(?<![A-Za-z0-9\-])((?:BR|DB|AI|OV|EV|UP|W|M|AUD|AZ|DEP|ESC|P|BAK|F|U|A|S|TM|FH|T|O)-?\d{1,3})(?![0-9])',T['SEC']))
defs=set()
for l in T['SEC'].split('\n'):
    m=re.match(r'^\| \*{0,2}((?:BR|DB|AI|OV|EV|UP|AUD|AZ|DEP|ESC|BAK|TM|FH|T|O|M|W|P|U|A|S)-?\d{1,3})\*{0,2}( \(S\))? \|',l)
    if m: defs.add(m.group(1))
refs=collections.Counter(re.findall(r'(?<![A-Za-z0-9\-])((?:BR|DB|AI|OV|EV|UP|AUD|AZ|DEP|ESC|BAK|T)-\d{1,3})(?![0-9])',T['PRD']))
missing={r:c for r,c in refs.items() if r not in defs}
P('== G. PRD references to Security IDs that have no defining row in Security 0.4')
P('  IDs referenced in PRD:',len(refs),' defined in Security 0.4:',len([r for r in refs if r in defs]),' missing:',len(missing))
P('  missing (id:count):',dict(sorted(missing.items())))
# 7 test-id sanity: PRD T-ids used vs Security T range
tmax=max(int(x[2:]) for x in defs if x.startswith('T-'))
P('  Security 0.4 test IDs defined: T-1..T-%d (%d rows)'%(tmax,len([x for x in defs if x.startswith('T-')])))
# 8 SD -> Security refs
refsSD=collections.Counter(re.findall(r'(?<![A-Za-z0-9\-])((?:BR|DB|AI|OV|EV|UP|AUD|AZ|DEP|ESC|BAK|T)-\d{1,3})(?![0-9])',T['SD']))
P('== H. SD references to Security IDs: referenced',len(refsSD),' missing in Security 0.4:',{r:c for r,c in refsSD.items() if r not in defs})
# 9 PRD T-ids that are reused with different meaning? count PRD rows citing T-33..T-54 outside section 11
open('/home/claude/recon/audit_out.txt','w').write('\n'.join(out))

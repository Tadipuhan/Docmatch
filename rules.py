"""Offline scope rules for DocMatch. Indices refer to nonempty content blocks."""
from __future__ import annotations
from dataclasses import dataclass
import re
import re
import difflib

START = re.compile(r'^\[DOCMATCH:START\s+id="([\w-]+)"(?:\s+mode="(exact|normalized)")?\]$', re.I)
END = re.compile(r'^\[DOCMATCH:END\]$', re.I)

@dataclass
class ParsedRules:
    blocks: list[str]
    embedded: set[int]
    groups: dict[str,list[int]]


def parse_embedded(blocks: list[str]) -> ParsedRules:
    clean=[]; selected=set(); groups={}; active=None
    for raw in blocks:
        line=raw.strip()
        match=START.fullmatch(line)
        if match:
            if active is not None: raise ValueError('Tag DOCMATCH:START bersarang tidak didukung.')
            active=match.group(1)
            if active in groups: raise ValueError(f'ID aturan duplikat: {active}')
            groups[active]=[]
            continue
        if END.fullmatch(line):
            if active is None: raise ValueError('DOCMATCH:END tanpa START.')
            if not groups[active]: raise ValueError(f'Aturan {active} tidak memiliki konten.')
            active=None
            continue
        if line.startswith('[DOCMATCH:'): raise ValueError(f'Tag tidak dikenali: {line[:100]}')
        if line:
            idx=len(clean);clean.append(raw)
            if active is not None:
                selected.add(idx);groups[active].append(idx)
    if active is not None: raise ValueError(f'Aturan {active} belum ditutup dengan DOCMATCH:END.')
    return ParsedRules(clean,selected,groups)


def resolve_scope(parsed:ParsedRules, visual:set[int], mode:str, all_blocks:bool=False)->set[int]:
    if all_blocks: return set(range(len(parsed.blocks)))
    if mode=='embedded': return set(parsed.embedded)
    if mode=='visual': return set(visual)
    if mode=='hybrid': return set(parsed.embedded)|set(visual)
    raise ValueError('Mode aturan tidak valid.')


def align_scope(reference:list[str], examined:list[str], selected:set[int]):
    """Conservative ordered alignment: only confident matches are mapped.

    Unmatched selected references are flagged for manual review, not asserted missing.
    Extra paragraphs outside selected scope are not compared.
    """
    def normalize(s):return ' '.join(s.casefold().split())
    a=[normalize(x) for x in reference];b=[normalize(x) for x in examined]
    anchors=difflib.SequenceMatcher(None,a,b,autojunk=False)
    mapping={}; uncertain=[]; used=set()
    for tag,i1,i2,j1,j2 in anchors.get_opcodes():
        if tag=='equal':
            for i,j in zip(range(i1,i2),range(j1,j2)):
                if i in selected: mapping[i]=j;used.add(j)
    for i in sorted(selected-set(mapping)):
        # Prefer proximity to preceding/following matched anchors, reject weak/ambiguous matches.
        left=max((j for k,j in mapping.items() if k<i),default=-1)
        right=min((j for k,j in mapping.items() if k>i),default=len(b))
        candidates=[]
        for j in range(left+1,right):
            if j in used:continue
            ratio=difflib.SequenceMatcher(None,a[i],b[j],autojunk=False).ratio()
            candidates.append((ratio,j))
        candidates.sort(reverse=True)
        if candidates and candidates[0][0]>=0.48 and (len(candidates)==1 or candidates[0][0]-candidates[1][0]>=0.06):
            mapping[i]=candidates[0][1];used.add(candidates[0][1])
        else: uncertain.append(i)
    return mapping,uncertain


@dataclass
class ScopedDifference:
    kind: str
    reference_index: int | None
    examined_index: int | None
    reference_text: str
    examined_text: str
    detail: str
    apply: bool = True

def selective_compare(reference:list[str],examined:list[str],scope:set[int]):
    mapping,uncertain=align_scope(reference,examined,scope)
    output=[]
    for i in sorted(scope):
        if i not in mapping:continue
        j=mapping[i]
        if reference[i]!=examined[j]:
            output.append(ScopedDifference('Perubahan',i,j,reference[i],examined[j],f'Paragraf rujukan {i+1} berbeda dari paragraf diperiksa {j+1}'))
    return output,uncertain,mapping

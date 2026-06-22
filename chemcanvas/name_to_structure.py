# -*- coding: utf-8 -*-
# This file is a part of ChemCanvas Program which is GNU GPLv3 licensed

import urllib.error
import urllib.parse
import urllib.request

from fileformat_molfile import Molfile
from fileformat_smiles import Smiles


class NameToStructureError(RuntimeError):
    pass


LOCAL_NAME_SMILES = {
    "water": "O",
    "methane": "C",
    "ethane": "CC",
    "propane": "CCC",
    "butane": "CCCC",
    "ethanol": "CCO",
    "ethyl alcohol": "CCO",
    "methanol": "CO",
    "acetone": "CC(=O)C",
    "benzene": "c1ccccc1",
    "toluene": "Cc1ccccc1",
    "acetic acid": "CC(=O)O",
}


def resolve_name_to_document(name, urlopen=None):
    """Resolve an English compound name to a ChemCanvas Document."""
    name = (name or "").strip()
    if not name:
        raise NameToStructureError("Enter an English chemical name.")

    lower_name = " ".join(name.lower().split())
    if lower_name in LOCAL_NAME_SMILES:
        return _document_from_smiles(LOCAL_NAME_SMILES[lower_name], name)

    return _document_from_pubchem(name, urlopen=urlopen)


def _document_from_smiles(smiles, name):
    reader = Smiles()
    try:
        doc = reader.read_string(smiles)
    except Exception as exc:
        raise NameToStructureError("Could not build the local structure for '%s'." % name) from exc
    if not doc or not doc.objects:
        raise NameToStructureError("Could not build the local structure for '%s'." % name)
    for obj in doc.objects:
        if obj.class_name == "Molecule":
            obj.name = name
    return doc


def _document_from_pubchem(name, urlopen=None):
    urlopen = urlopen or urllib.request.urlopen
    encoded_name = urllib.parse.quote(name.replace(" ", "-"), safe="")
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/%s/SDF" % encoded_name
    try:
        with urlopen(url, timeout=10) as response:
            result = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            exc.close()
        except Exception:
            pass
        if exc.code == 404:
            raise NameToStructureError("No structure found for '%s'." % name) from exc
        raise NameToStructureError("PubChem lookup failed for '%s'." % name) from exc
    except Exception as exc:
        raise NameToStructureError("Could not connect to PubChem for '%s'." % name) from exc

    reader = Molfile()
    doc = reader.readFromString(result)
    if not doc or not doc.objects:
        raise NameToStructureError("PubChem did not return a readable structure for '%s'." % name)

    for obj in doc.objects:
        if obj.class_name == "Molecule":
            obj.name = name
    return doc

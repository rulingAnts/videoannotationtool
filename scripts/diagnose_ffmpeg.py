import json
from vat.utils.resources import resolve_ff_tools
print(json.dumps(resolve_ff_tools(), indent=2))

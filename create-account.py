#!/usr/bin/env python
import base64
from typing import List, Any, Optional
import algosdk


sk, pk = algosdk.account.generate_account()
print(f"""
  private_key: {sk}
  public_key: {pk}
""")

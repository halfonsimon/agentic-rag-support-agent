"""Tools return JSON strings suitable for model tool responses."""

from .calculator import calculator
from .customers import authenticate, get_customer
from .policies import read_policies
from .products import filter_products, search_products

TOOL_IMPLS = {
    "search_products": search_products,
    "filter_products": filter_products,
    "get_customer": get_customer,
    "authenticate": authenticate,
    "read_policies": read_policies,
    "calculator": calculator,
}

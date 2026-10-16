import re

def named_constraints_script(schema: dict) -> dict:
    tables = schema.get("tables", {})
    sorted_tables = sorted(tables.keys())
    
    add_lines = []
    validate_fk_lines = []
    validate_ck_lines = []
    
    seen_names = set()

    def add_name(name: str):
        if len(name) > 63:
            name = name[:63]
        if name in seen_names:
            raise ValueError(f"Дубльоване ім'я обмеження: {name}")
        seen_names.add(name)
        return name

    # 1. PRIMARY KEY та UNIQUE
    for tname in sorted_tables:
        tdata = tables[tname]
        pk = tdata.get("pk", [])
        if pk:
            cols_str = "_".join(pk)
            cname = add_name(f"pk_{tname}")
            cols_quoted = ", ".join([f'"{c}"' for c in pk])
            add_lines.append(f'ALTER TABLE "{tname}" ADD CONSTRAINT "{cname}" PRIMARY KEY ({cols_quoted});')
            
        uniques = tdata.get("unique", [])
        for ucols in uniques:
            cols_str = "_".join(ucols)
            cname = add_name(f"uq_{tname}_{cols_str}")
            cols_quoted = ", ".join([f'"{c}"' for c in ucols])
            add_lines.append(f'ALTER TABLE "{tname}" ADD CONSTRAINT "{cname}" UNIQUE ({cols_quoted});')

    # 2. FOREIGN KEYS
    for tname in sorted_tables:
        tdata = tables[tname]
        fks = tdata.get("fks", [])
        for fk in fks:
            fcols = fk.get("columns", [])
            rtable = fk.get("ref_table")
            rcols = fk.get("ref_columns", [])
            on_delete = fk.get("on_delete", "NO ACTION")
            
            cols_str = "_".join(fcols)
            cname = add_name(f"fk_{tname}_{cols_str}")
            
            fcols_q = ", ".join([f'"{c}"' for c in fcols])
            rcols_q = ", ".join([f'"{c}"' for c in rcols])
            
            constraint_def = (
                f'ALTER TABLE "{tname}" ADD CONSTRAINT "{cname}" '
                f'FOREIGN KEY ({fcols_q}) REFERENCES "{rtable}" ({rcols_q})'
            )
            if on_delete and on_delete != "NO ACTION":
                constraint_def += f" ON DELETE {on_delete}"
            constraint_def += " NOT VALID;"
            
            add_lines.append(constraint_def)
            validate_fk_lines.append(f'ALTER TABLE "{tname}" VALIDATE CONSTRAINT "{cname}";')

    # 3. CHECKS
    for tname in sorted_tables:
        tdata = tables[tname]
        checks = tdata.get("checks", [])
        for idx, check_expr in enumerate(checks, start=1):
            cname = add_name(f"ck_{tname}_{idx}")
            add_lines.append(f'ALTER TABLE "{tname}" ADD CONSTRAINT "{cname}" CHECK ({check_expr}) NOT VALID;')
            validate_ck_lines.append(f'ALTER TABLE "{tname}" VALIDATE CONSTRAINT "{cname}";')

    add_script = "\n".join(add_lines)
    validate_script = "\n".join(validate_fk_lines + validate_ck_lines)

    return {
        "add": add_script,
        "validate": validate_script
    }
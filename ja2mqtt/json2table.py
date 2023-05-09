# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

import re
import sys
import os
import collections
import json

from .utils import PathDef, remove_ansi_escape


class Table:
    def __init__(self, table_def, sort_cols, sort_reverse):
        self.table_def = table_def
        self.sort_def = self._sort_def(sort_cols, table_def)
        self.sort_reverse = sort_reverse

    def _sort_def(self, sort_cols, table_def):
        if sort_cols is None:
            return None
        sort_def = collections.OrderedDict.fromkeys(
            [s.strip().upper() for s in sort_cols.split(",")]
        )
        for e in self.table_def:
            if e.get("value"):
                params = PathDef(e.get("value")).params(e["name"])
                for s in sort_def.keys():
                    for k, v in params.params.items():
                        if v.upper() == s:
                            sort_def[s] = "{%s}" % k
                            break
        return sort_def

    def format_item(
        self, cdef, value, skipformat=False, entry=None, adjust=True, global_format=None
    ):
        if cdef.get("format") and not skipformat:  # and value is not None:
            try:
                v = str(cdef["format"](cdef, value, entry))
            except:
                v = "E!"
        else:
            v = str(value) if value is not None else "-"

        if global_format:
            v = global_format(cdef, v, entry)

        asize = 0
        if adjust and cdef.get("_len"):
            asize = cdef["_len"] + 2
        if cdef.get("mlen") and len(remove_ansi_escape(v)) > cdef["mlen"]:
            v = v[: cdef["mlen"] - 1] + "…"

        if not cdef.get("justify") or cdef.get("justify") == "left":
            return f"{v}" + "".join(
                [" " for x in range(asize - len(remove_ansi_escape(v)))]
            )
        if cdef.get("justify") == "right":
            return (
                "".join([" " for x in range(asize - len(remove_ansi_escape(v)))])
                + f"{v}"
            )

    def get_field(self, field_name, data):
        d = data
        for f in field_name.split("."):
            try:
                d = d.get(f)
            except:
                return None
        return d

    def eval_value(self, value, data):
        if not value:
            return None
        # get fields placeholders: {placeholder}
        params = list(set(re.findall("\{[a-zA-Z0-9_\-\.]+\}", value)))
        val = value
        if len(params) > 1:
            for k in params:
                val = val.replace(k, str(self.get_field(k[1:-1], data)))
            return val
        if len(params) == 1:
            return self.get_field(params[0][1:-1], data)
        if len(params) == 0:
            return value

    def calc_col_sizes(self):
        for cdef in self.table_def:
            l = len(
                self.format_item(
                    cdef, cdef["name"], skipformat=True, entry=None, adjust=False
                )
            )
            if cdef.get("_len") is None or l > cdef["_len"]:
                if cdef.get("mlen") is not None and l > cdef["mlen"]:
                    l = cdef["mlen"]
                cdef["_len"] = l

        for e in self.data:
            for cdef in self.table_def:
                l = len(
                    remove_ansi_escape(
                        self.format_item(
                            cdef,
                            self.eval_value(cdef.get("value"), e),
                            skipformat=False,
                            entry=e,
                            adjust=False,
                        )
                    )
                )
                if cdef.get("_len") is None or l > cdef["_len"]:
                    if cdef.get("mlen") is not None and l > cdef["mlen"]:
                        l = cdef["mlen"]
                    cdef["_len"] = l

    def getTerminalCols(self):
        cols = 1000
        try:
            cols = int(os.popen("stty size", "r").read().split()[1])
        except Exception as e:
            sys.stderr.write("Cannot determine terminal dimensions: %s/n" % (str(e)))
            pass
        return cols

    def display(
        self, data, noterm=False, global_format=None, format=None, csv_delim=";"
    ):
        if format is not None and format not in ["json", "csv"]:
            raise Exception(
                "Invalid format value {format}. The allowed values are 'csv' or 'json'."
            )

        # sort data
        if self.sort_def is not None:
            data = sorted(
                data,
                key=lambda item: tuple(
                    self.eval_value(v, item)
                    for k, v in self.sort_def.items()
                    if v is not None
                ),
                reverse=self.sort_reverse,
            )

        # calc
        self.data = data
        self.calc_col_sizes()

        # display header
        lines = []
        line = []
        delim = csv_delim if format is not None else ""
        for cdef in self.table_def:
            if format is None:
                line.append(
                    self.format_item(
                        cdef,
                        cdef["name"],
                        skipformat=True,
                        entry=None,
                        adjust=not (noterm),
                    )
                )
            else:
                line.append('"' + cdef["name"] + '"')
        lines.append(delim.join(line))

        def _wrap_str(val):
            if isinstance(val, str):
                return f'"{val}"'
            if isinstance(val, list):
                return ",".join(val)
            return str(val)

        # display rows
        for e in self.data:
            line = []
            for cdef in self.table_def:
                if format is None:
                    line.append(
                        self.format_item(
                            cdef,
                            self.eval_value(cdef.get("value"), e),
                            skipformat=False,
                            entry=e,
                            adjust=not (noterm),
                            global_format=global_format,
                        )
                    )
                else:
                    line.append(_wrap_str(self.eval_value(cdef.get("value"), e)))
            lines.append(delim.join(line))

        if not (noterm) and format is None:
            cols = self.getTerminalCols()
        else:
            cols = 100000

        if format is None or format == "csv":
            for line in lines:
                sys.stdout.write("%s\n" % line[0:cols])
        else:
            header = None
            data = []
            for line in lines:
                items = [x.replace('"', "") for x in line.split(";")]
                if header is None:
                    header = items
                else:
                    row = {}
                    for inx, value in enumerate(items):
                        row[header[inx]] = value
                    data.append(row)
            print(json.dumps(data, indent=4, sort_keys=True, default=str))
        return len(lines)

    def describe(self, noterm=False):
        mlen = 0
        for cdef in self.table_def:
            if cdef.get("name") is not None and len(cdef["name"]) > mlen:
                mlen = len(cdef["name"])

        if not (noterm):
            cols = self.getTerminalCols()
        else:
            cols = 1000

        for cdef in self.table_def:
            if cdef.get("name") is not None:
                line = "{name}  {descr}\n".format(
                    name=cdef["name"].ljust(mlen), descr=cdef.get("help", "n/a")
                )
                sys.stdout.write(line[0:cols])

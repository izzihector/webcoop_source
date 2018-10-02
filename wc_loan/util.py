# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math

def prepare_insert_sql(cr, uid, model, fields):
    extra_fields = ",".join([
        "create_uid",
        "write_uid",
        "create_date",
        "write_date"
    ])

    seq = "nextval('%s_id_seq')" % model
    v =  ["%%(%s)s" % f for f in fields]
    v += [
        "%s" % uid,
        "%s" % uid,
        "(now() at time zone 'UTC')",
        "(now() at time zone 'UTC')"
    ]

    sql = "INSERT INTO %s (id,%s,%s) VALUES (%s,%s) RETURNING id;" % (
        model,
        ",".join(fields),
        extra_fields,

        seq,
        ",".join(v)
    )

    return sql


def prepare_insert_sql2(cr, uid, model, values):
    fields = values[0].keys()
    extra_fields = ",".join([
        "create_uid",
        "write_uid",
        "create_date",
        "write_date"
    ])

    sql = "INSERT INTO %s (id,%s,%s) VALUES" % (
        model,
        extra_fields,
        ",".join(fields),
    )

    seq = "nextval('%s_id_seq')" % model
    vsql = "(%s" % seq
    vsql += ",%s,%s,now() at time zone 'UTC',now() at time zone 'UTC'" % (uid, uid)
    vsql += (",%s" * len(fields))
    vsql += ")"

    #vals = [cr.mogrify(vsql, values[k]) for k in fields]
    vals = []
    for ln in values:
        v = tuple([ln[k] for k in fields])
        vals.append(cr.mogrify(vsql, v))

    #(%s,%s) RETURNING id;
    return sql + (",".join(vals)) + " RETURNING id;"



#

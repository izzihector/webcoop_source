# -*- coding: utf-8 -*-
###############################################
# EzTech Software & Consultancy Inc. (c) 2017
###############################################
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math

def merge_same(moves):
    totals = {}
    res = []
    for m0 in moves:
        m = m0[2]
        if m.get('name')=='/':
            k = "%s-%s-%s-%s" % (
                m.get('journal_id'),
                m.get('date'),
                m.get('date'),
                m.get('account_id')
            )
            if k not in totals:
                totals[k] = dict(m)
            else:
                totals[k]['debit'] += m['debit']
                totals[k]['credit'] += m['credit']
        else:
           res.append(m0)

    for k in totals:
       #res.insert(0, [0, 0, totals[k]])
       res.append([0, 0, totals[k]])

    return res

def to_dr_cr(amt):
    if amt>=0.0:
        return round(amt,2), 0.00
    else:
        return 0.00, - round(amt,2)

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

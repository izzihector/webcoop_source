{
    'name': 'Web Coop - Ver1.2 (Loans X-days Schedule,etc)',
    'version': "1.2",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.2",
    'description': """
        |   version 10.0.1.1  Add manually x days period for loan schedule
        |   version 10.0.1.2
        |     f534:  Add 364 days in year for loan (this is mainly for weekly or 14 days schedule)
        |     f535:  Add Advance Interest Deduction (this is only for straight loan)
        |     f536:  Hide approved date from loan registration view if draft loan
        |     f538:  Add additional setting in loan type , so that you can set minimum principal an maximum principal amount to be inputte. Likewise, range of interest rate and no.of payments also can be set.
        |     f540:  Draft transaction of saving , and collection will be automatically deleted by daily closing           
        |     f541:  Change attribute of [schecule] drop down in collection entry ,from required field to not required field          
        |     f542:  Add tag on membership form about collection data         
        |     f543:  In case of straight interest , term_payments cannot be calculated before generate schedule
        |     f545:  Add threshold in loan type configuration ,for check payment in loan registration (Before check payment threshold is static 50000)
        |     f547:  (Bug)Loan officer cannot gerenate schedule
        |     f548:  (Bug)Deduction items are removed and re-created when saving after update loan basic info
    """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_member','wc_loan','wc_posting','wc_loan_epr','wc_loan_xdays_schedule',
        'wc_collection','wc_collection_other'
    ],
    'data': [
        "f535/loan_type_view_ex.xml",
        "f535/loan_view_ex.xml",
        "f536/loan_view_ex.xml",
        "f538/loan_type_view_ex.xml",
        "f540/posting_view_ex.xml",
        "f541/collection_view_ex.xml",
        "f542/member_view_ex.xml",
        "f543/loan_view_ex.xml",
        "f545/loan_type_view_ex.xml",
        "f547/security/ir.model.access.csv",
        "f548/loan_view_ex.xml",
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
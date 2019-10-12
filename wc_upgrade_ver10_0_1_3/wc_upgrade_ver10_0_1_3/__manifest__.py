{
    'name': 'Web Coop - Ver1.3 ',
    'version': "1.3",
    'category': "Generic Modules",
    'license':"Other proprietary",
    'summary': "Upgrade ver 1.3",
    'description': """
        |   version 10.0.1.3 
        |    b551:Count of loan link button on member ship form is incorrect
        |         fixed bug: pastdue loan was not counted
        |    b561:Loan Restructuring is not working
        |         fixed bug: loan restructure was failed in case of xdays schedule
        |    b572:System error When select co-maker in members form
        |    f567:Upfront interest apply also on diminishing type interest
        |         change title of interest advance deduction to Upfront interest
        |         allow upfront interest in case of diminishing loan also , not only straight interest
        |    f568:Add feature for default loan amount 
        |         add default loan amount field in loan type configuration.
        |         if the amount is set, the amount appear on loan registration form on selecting the loan type
        |    f570:Allow linkage of member's data from loan registration
        |         add linkage for opening member form on maker and co-maker field on loan register form
        |    b575:Minus net amount should be rejected in loan register
        |         Add validation check if net_amount is minus in case the loan has deduction items. 
    """,
    'author': 'E-supportlink,ltd',
    'depends': [
        'wc_upgrade_ver10_0_1_2'
    ],
    'data': [
        "f567/loan_type_view_ex.xml",
        "f567/loan_view_ex.xml",
        "f568/loan_type_view_ex.xml",
        "f570/loan_view_ex.xml",
    ],
    'demo': [],
    'qweb': [],
    'test': [],
    'installable': True,
    'application': True,
    'auto_install':False,
}
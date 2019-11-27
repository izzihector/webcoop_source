# -*- coding: utf-8 -*-
{
    'name': 'Web Coop - Dividend Calculation Patern 1',
    'version': "1.0",
    'category': "Generic Modules",
    'summary': "Dividend Module for Web Coop System (",
    'description': """
====================================
Process for Diviend and Patronage 
====================================
 * 1.Get net surplus ( this is from Balance Sheet , as [profit to report] ) manually
    [S] (net surplus) = refer and get from balance sheet   (manually)
 * 2.Decide percentage of distribution(x%) for share capital divident and patronage , and get total avail amount for distribution
    [T1] (Total Amount for Distribution) = [S] * x%     (manually)
 * 3.Decide percentage for divident (a%) , and patronage(100-a%)  , and then calculate total divident amount(TD) and total patronage amount(TP)
    [TD] (Total Avail amount for divident distribution) = [T1] * a%    (manually)
    [TP] (Total Avail amount for patronage refund)     = [T1] * (100-a)%    (manually)    
  ---------- from now on ,  open wizard and enter [TD] and [TP] and proceed system calculation logic below -------------        
 * 4.Calculation of divident amount (logic for get divident rate)
    s1 get [TSM] (Total share month) of each member
     [TSM] = get monthly balance of each member. Monthly balance will be the balance of the 7th date of each month.
     (if cbu deposit is done on 8th date onward , the deposit amount will be reflected as succeeding month's balance)
     summarize the monthly balance in the account year
    s2. get [ASM] (Average share month) of each member
     [ASM] = [TSM] / 12
    s3. get [TASM] (Total Average share month)
     [TASM] = Summary of every member's [TSM]  (including left member)
    s4. get [R1]  (Intersest rate on share capital)
     [R1] = [TD]  (total divident calculated by 1-3 )  divided by [TASM]
     Round at 7th decimal degit
    s5.calculate each [IISC](Individual Interest on Share Capital)
     [IISC] = [ASM]  * [R1]        
 * 5.Calculation of patronage refund rate (logic for get patronage refund amount)    
    s1.get total interest income amount([Int on LOAN] from each member of the year     
     [Int On LOAN] = Summarize credit amount of account move transaction whose coa title is set as interest income gl account ,and whose transaction date is in the year
    s2. get total [Int On LOAN]     
     [Total Int ON LOAN] = summarize every member's [Int On LOAN]
    s3. get [PR] (patronaze rate )     
     [PR] = [TP] /[Total Int ON LOAN] 
    """
    ,
    'author': 'E-supportlink',
    'website': '',
    'depends': [
        'wc',
        'wc_account',
        'wc_loan',
        'account_accountant',
        'wc_dividend'
    ],
    'init_xml': [],
    'data': [
        'data/res_company_data.xml',
        'dividend_patern1_view.xml',
        'res_company_view_ex.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}

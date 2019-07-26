# WebCOOP Revisions

Fix #269
- wc_loan - needs module upgrade
- add filter on accounts on loan deduction view.

Add feature #271
- initial force bulk approvals for data migration.

Add feature #274
- passbook and validation print formatting

Fix #277
- change record id with rule of "chartxxxxxx_en"(xxxxxx=code).
  (except for the one having special record id like "ao_inventory")

Fix #279
-speed up bulk approve 
-for speed up
-1.change ORM api to sql usage.
-Other 
-1.put max count for suspend and commit the data upto the limit count
-2.change bulk loan approval to approve only loan header and don't create amortization sched and loan detail(these should be import seperately)
-3.add check if selected branch has no daily closing date (for avoid risk for affection to other branch's data)
-4.change menu
-5.add access group for data migration

Fix #528 (20190726
-Add some field on membership form and Hide some fields on CBU , SAVING form (USEMB coop request )


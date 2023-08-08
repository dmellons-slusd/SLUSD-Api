select cd 'sc'
,nm 'name'
,pr 'principal', 
pem 'principal_email'
,ad 'street_address'
,cy 'city'
,st 'state'
,zc 'zip'
,ac 'area_code'
,tl 'phone_number'
,concat(ad , ', ' , cy , ', ' , st , ' ' , zc )as 'mailing_address'
, concat('(',ac,') ', SUBSTRING(tl,0,4),'-',SUBSTRING(tl,4,7)) as 'full_phone'

from LOC
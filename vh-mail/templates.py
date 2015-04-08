EXIM_CONFIG = r"""
#--AUTOMATICALLY GENERATED - DO NO EDIT!

#--MACROS

SMTP_PORT = 25
LOCAL_INTERFACES = <; 0.0.0.0.25 ; 0.0.0.0.465 ; [::0]:25 ; [::0]:465
CONFDIR = /etc/exim4

LOCAL_DOMAINS = %(local_domains)s
ETC_MAILNAME = %(mailname)s
LOCAL_DELIVERY = mail_spool
CHECK_RCPT_LOCAL_LOCALPARTS = ^[.] : ^.*[@%%!/|`#&?]
CHECK_RCPT_REMOTE_LOCALPARTS = ^[./|] : ^.*[@%%!`#&?] : ^.*/\\.\\./

%(dkim_enable)s
DKIM_SELECTOR = %(dkim_selector)s
DKIM_PRIVATE_KEY = %(dkim_private_key)s
DKIM_CANON = relaxed
DKIM_STRICT = 1

%(tls_enable)s
TLS_ADVERTISE_HOSTS = *
TLS_CERTIFICATE = %(tls_certificate)s
TLS_PRIVATEKEY = %(tls_privatekey)s
TLS_VERIFY_CERTIFICATES = ${if exists{/etc/ssl/certs/ca-certificates.crt} {/etc/ssl/certs/ca-certificates.crt} {/dev/null}}

COURIERSOCKET = %(courier_authsocket)s

ACL_SMTP_MAIL = acl_check_mail
ACL_SMTP_RCPT = acl_check_rcpt
ACL_SMTP_DATA = acl_check_data

#--CONFIGURATION

%(custom_mta_config)s

daemon_smtp_ports = SMTP_PORT
local_interfaces = LOCAL_INTERFACES
domainlist local_domains = LOCAL_DOMAINS
qualify_domain = ETC_MAILNAME

gecos_pattern = ^([^,:]*)
gecos_name = $1

acl_smtp_mail = ACL_SMTP_MAIL
acl_smtp_rcpt = ACL_SMTP_RCPT
acl_smtp_data = ACL_SMTP_DATA

# spamd_address = 127.0.0.1 783

local_from_check = false
local_sender_retain = true
untrusted_set_sender = *

ignore_bounce_errors_after = 2d
timeout_frozen_after = 7d
freeze_tell = postmaster
spool_directory = /var/spool/exim4

trusted_users = uucp

.ifdef TLS_ENABLE
tls_on_connect_ports = 465
tls_advertise_hosts = TLS_ADVERTISE_HOSTS
tls_certificate = TLS_CERTIFICATE
tls_privatekey = TLS_PRIVATEKEY
tls_verify_certificates = TLS_VERIFY_CERTIFICATES
.endif


begin acl

%(custom_mta_acl)s

acl_check_mail:
  .ifdef CHECK_MAIL_HELO_ISSUED
  deny
    message = no HELO given before MAIL command
    condition = ${if def:sender_helo_name {no}{yes}}
  .endif

  accept

acl_check_rcpt:
  accept
    hosts = :
    control = dkim_disable_verify

  .ifdef CHECK_RCPT_LOCAL_LOCALPARTS
  deny
    domains = +local_domains
    local_parts = CHECK_RCPT_LOCAL_LOCALPARTS
    message = restricted characters in address
  .endif

  .ifdef CHECK_RCPT_REMOTE_LOCALPARTS
  deny
    domains = !+local_domains
    local_parts = CHECK_RCPT_REMOTE_LOCALPARTS
    message = restricted characters in address
  .endif

  accept
    .ifndef CHECK_RCPT_POSTMASTER
    local_parts = postmaster
    .else
    local_parts = CHECK_RCPT_POSTMASTER
    .endif
    domains = +local_domains

  .ifdef CHECK_RCPT_VERIFY_SENDER
  deny
    message = Sender verification failed
    !verify = sender
  .endif

  accept
    authenticated = *
    control = submission/sender_retain
    control = dkim_disable_verify

  require
    message = relay not permitted
    domains = +local_domains

  require
    verify = recipient

  .ifdef CHECK_RCPT_SPF
  deny
    message = [SPF] $sender_host_address is not allowed to send mail from \
              ${if def:sender_address_domain {$sender_address_domain}{$sender_helo_name}}.  \
              Please see \
          http://www.openspf.org/Why?scope=${if def:sender_address_domain \
              {mfrom}{helo}};identity=${if def:sender_address_domain \
              {$sender_address}{$sender_helo_name}};ip=$sender_host_address
    log_message = SPF check failed.
    condition = ${run{/usr/bin/spfquery.mail-spf-perl --ip \
                   \"$sender_host_address\" --identity \
                   ${if def:sender_address_domain \
                       {--scope mfrom  --identity \"$sender_address\"}\
                       {--scope helo --identity  \"$sender_helo_name\"}}}\
                   {no}{${if eq {$runrc}{1}{yes}{no}}}}

  defer
    message = Temporary DNS error while checking SPF record.  Try again later.
    condition = ${if eq {$runrc}{5}{yes}{no}}

  warn
    condition = ${if <={$runrc}{6}{yes}{no}}
    add_header = Received-SPF: ${if eq {$runrc}{0}{pass}\
                                {${if eq {$runrc}{2}{softfail}\
                                 {${if eq {$runrc}{3}{neutral}\
                  {${if eq {$runrc}{4}{permerror}\
                   {${if eq {$runrc}{6}{none}{error}}}}}}}}}\
                } client-ip=$sender_host_address; \
                ${if def:sender_address_domain \
                   {envelope-from=${sender_address}; }{}}\
                helo=$sender_helo_name

  warn
    log_message = Unexpected error in SPF check.
    condition = ${if >{$runrc}{6}{yes}{no}}
  .endif


  .ifdef CHECK_RCPT_IP_DNSBLS
  warn
    dnslists = CHECK_RCPT_IP_DNSBLS
    add_header = X-Warning: $sender_host_address is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
    log_message = $sender_host_address is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
  .endif

  .ifdef CHECK_RCPT_DOMAIN_DNSBLS
  warn
    !senders = ${if exists{CONFDIR/local_domain_dnsbl_whitelist}\
                    {CONFDIR/local_domain_dnsbl_whitelist}\
                    {}}
    dnslists = CHECK_RCPT_DOMAIN_DNSBLS
    add_header = X-Warning: $sender_address_domain is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
    log_message = $sender_address_domain is listed at $dnslist_domain ($dnslist_value: $dnslist_text)
  .endif

  accept


acl_check_data:

  deny
    message = Message headers fail syntax check
    !verify = header_syntax

  accept

begin routers

%(custom_mta_routers)s

vforward:
  debug_print = "R: vforward for $local_part@$domain"
  driver = redirect
  allow_defer
  allow_fail
  domains = +local_domains
  file = %(mailforward)s/$local_part@$domain
  file_transport = address_file
  pipe_transport = address_pipe
  %(custom_mta_local_router)s

vdomain:
  debug_print = "R: vdomain for $local_part@$domain"
  driver = accept
  domains = dsearch;%(maildomains)s
  local_parts = lsearch;%(maildomains)s/$domain
  transport = vmail
  %(custom_mta_local_router)s

dnslookup:
  debug_print = "R: dnslookup for $local_part@$domain"
  driver = dnslookup
  domains = ! +local_domains
  transport = remote_smtp
  headers_remove = received
  same_domain_copy_routing = yes
  ignore_target_hosts = 0.0.0.0 : 127.0.0.0/8 : 192.168.0.0/16 :\
                        172.16.0.0/12 : 10.0.0.0/8 : 169.254.0.0/16
  no_more

nonlocal:
  debug_print = "R: nonlocal for $local_part@$domain"
  driver = redirect
  domains = ! +local_domains
  allow_fail
  data = :fail: Mailing to remote domains not supported
  no_more


COND_LOCAL_SUBMITTER = "\
               ${if match_ip{$sender_host_address}{:@[]}\
                    {1}{0}\
        }"

real_local:
  debug_print = "R: real_local for $local_part@$domain"
  driver = accept
  domains = +local_domains
  condition = COND_LOCAL_SUBMITTER
  local_part_prefix = real-
  check_local_user
  transport = LOCAL_DELIVERY
  %(custom_mta_local_router)s

procmail:
  debug_print = "R: procmail for $local_part@$domain"
  driver = accept
  domains = +local_domains
  check_local_user
  transport = procmail_pipe
  # emulate OR with "if exists"-expansion
  require_files = ${local_part}:\
                  ${if exists{/etc/procmailrc}\
                    {/etc/procmailrc}{${home}/.procmailrc}}:\
                  +/usr/bin/procmail
  no_verify
  no_expn

maildrop:
  debug_print = "R: maildrop for $local_part@$domain"
  driver = accept
  domains = +local_domains
  check_local_user
  transport = maildrop_pipe
  require_files = ${local_part}:${home}/.mailfilter:+/usr/bin/maildrop
  no_verify
  no_expn


local_user:
  debug_print = "R: local_user for $local_part@$domain"
  driver = accept
  domains = +local_domains
  check_local_user
  local_parts = ! root
  transport = LOCAL_DELIVERY
  cannot_route_message = Unknown user
  %(custom_mta_local_router)s

mail4root:
  debug_print = "R: mail4root for $local_part@$domain"
  driver = redirect
  domains = +local_domains
  data = /var/mail/mail
  file_transport = address_file
  local_parts = root
  user = mail
  group = mail
  %(custom_mta_local_router)s


begin transports

%(custom_mta_transports)s


vmail:
  debug_print = "T: vmail for $local_part@$domain"
  driver = appendfile
  user = mail
  maildir_format = true
  directory = %(mailroot)s/$domain/$local_part
  create_directory
  delivery_date_add
  envelope_to_add
  return_path_add
  group = mail
  mode = 0600

mail_spool:
  debug_print = "T: appendfile for $local_part@$domain"
  driver = appendfile
  file = /var/mail/$local_part
  delivery_date_add
  envelope_to_add
  return_path_add
  group = mail
  mode = 0660
  mode_fail_narrower = false

maildir_home:
  debug_print = "T: maildir_home for $local_part@$domain"
  driver = appendfile
  .ifdef MAILDIR_HOME_MAILDIR_LOCATION
  directory = MAILDIR_HOME_MAILDIR_LOCATION
  .else
  directory = $home/Maildir
  .endif
  .ifdef MAILDIR_HOME_CREATE_DIRECTORY
  create_directory
  .endif
  .ifdef MAILDIR_HOME_CREATE_FILE
  create_file = MAILDIR_HOME_CREATE_FILE
  .endif
  delivery_date_add
  envelope_to_add
  return_path_add
  maildir_format
  .ifdef MAILDIR_HOME_DIRECTORY_MODE
  directory_mode = MAILDIR_HOME_DIRECTORY_MODE
  .else
  directory_mode = 0700
  .endif
  .ifdef MAILDIR_HOME_MODE
  mode = MAILDIR_HOME_MODE
  .else
  mode = 0600
  .endif
  mode_fail_narrower = false

maildrop_pipe:
  debug_print = "T: maildrop_pipe for $local_part@$domain"
  driver = pipe
  path = "/bin:/usr/bin:/usr/local/bin"
  command = "/usr/bin/maildrop"
  return_path_add
  delivery_date_add
  envelope_to_add

procmail_pipe:
  debug_print = "T: procmail_pipe for $local_part@$domain"
  driver = pipe
  path = "/bin:/usr/bin:/usr/local/bin"
  command = "/usr/bin/procmail"
  return_path_add
  delivery_date_add
  envelope_to_add

remote_smtp:
  debug_print = "T: remote_smtp for $local_part@$domain"
  driver = smtp
  .ifdef DKIM_ENABLE
    dkim_domain = $sender_address_domain
    .ifdef DKIM_SELECTOR
    dkim_selector = DKIM_SELECTOR
    .endif
    .ifdef DKIM_PRIVATE_KEY
    dkim_private_key = DKIM_PRIVATE_KEY
    .endif
    .ifdef DKIM_CANON
    dkim_canon = DKIM_CANON
    .endif
    .ifdef DKIM_STRICT
    dkim_strict = DKIM_STRICT
    .endif
    .ifdef DKIM_SIGN_HEADERS
    dkim_sign_headers = DKIM_SIGN_HEADERS
    .endif
  .endif

address_file:
  debug_print = "T: address_file for $local_part@$domain"
  driver = appendfile
  delivery_date_add
  envelope_to_add
  return_path_add

address_pipe:
  debug_print = "T: address_pipe for $local_part@$domain"
  driver = pipe
  return_fail_output

address_reply:
  debug_print = "T: autoreply for $local_part@$domain"
  driver = autoreply



begin retry
*                      *           F,2h,15m; G,16h,1h,1.5; F,4d,6h


begin rewrite

begin authenticators

login:
  driver = plaintext
  public_name = LOGIN
  server_prompts = Username:: : Password::
  server_condition = ${extract {address} {${readsocket{COURIERSOCKET} \
      {AUTH ${strlen:exim\nlogin\n$1\n$2\n}\nexim\nlogin\n$1\n$2\n} }} {yes} fail}
  server_set_id = $1

plain:
  driver = plaintext
  public_name = PLAIN
  server_prompts = :
  server_condition = ${extract {address} {${readsocket{COURIERSOCKET} \
      {AUTH ${strlen:exim\nlogin\n$2\n$3\n}\nexim\nlogin\n$2\n$3\n} }} {yes} fail}
  server_set_id = $2
  server_advertise_condition = ${if eq{$tls_cipher}{} {no} {yes}}
"""

COURIER_AUTHRC = """
authmodulelist="authuserdb authpam"
daemons=5
authdaemonvar=%(courier_authsocket)s
DEBUG_LOGIN=0
DEFAULTOPTIONS=""
LOGGEROPTS=""
"""

COURIER_IMAP = """
ADDRESS=0
PORT=143
MAXDAEMONS=40
MAXPERIP=20
PIDFILE=/var/run/courier/imapd.pid
TCPDOPTS="-nodnslookup -noidentlookup"
LOGGEROPTS="-name=imapd"
IMAP_CAPABILITY="IMAP4rev1 UIDPLUS CHILDREN NAMESPACE THREAD=ORDEREDSUBJECT THREAD=REFERENCES SORT QUOTA IDLE"
IMAP_KEYWORDS=1
IMAP_ACL=1
IMAP_CAPABILITY_ORIG="IMAP4rev1 UIDPLUS CHILDREN NAMESPACE THREAD=ORDEREDSUBJECT THREAD=REFERENCES SORT QUOTA AUTH=CRAM-MD5 AUTH=CRAM-SHA1 AUTH=CRAM-SHA256 IDLE"
IMAP_PROXY=0
IMAP_IDLE_TIMEOUT=60
IMAP_MAILBOX_SANITY_CHECK=1
IMAP_CAPABILITY_TLS="$IMAP_CAPABILITY AUTH=PLAIN"
IMAP_CAPABILITY_TLS_ORIG="$IMAP_CAPABILITY_ORIG AUTH=PLAIN"
IMAP_DISABLETHREADSORT=0
IMAP_CHECK_ALL_FOLDERS=0
IMAP_OBSOLETE_CLIENT=0
IMAP_UMASK=022
IMAP_ULIMITD=131072
IMAP_USELOCKS=1
IMAP_SHAREDINDEXFILE=/etc/courier/shared/index
IMAP_ENHANCEDIDLE=0
IMAP_TRASHFOLDERNAME=Trash
IMAP_EMPTYTRASH=Trash:7
IMAP_MOVE_EXPUNGE_TO_TRASH=0
SENDMAIL=/usr/sbin/sendmail
HEADERFROM=X-IMAP-Sender
IMAPDSTART=YES
MAILDIRPATH=Maildir
"""

COURIER_IMAPS = """
SSLPORT=993
SSLADDRESS=0
SSLPIDFILE=/var/run/courier/imapd-ssl.pid
SSLLOGGEROPTS="-name=imapd-ssl"
IMAPDSSLSTART=YES
IMAPDSTARTTLS=YES
IMAP_TLS_REQUIRED=0
COURIERTLS=/usr/bin/couriertls
TLS_KX_LIST=ALL
TLS_COMPRESSION=ALL
TLS_CERTS=X509
TLS_CERTFILE=%(tls_pem)s
TLS_TRUSTCERTS=/etc/ssl/certs
TLS_VERIFYPEER=NONE
TLS_CACHEFILE=/var/lib/courier/couriersslcache
TLS_CACHESIZE=524288
TLS_DHPARAMS=/etc/courier/dhparams.pem
MAILDIRPATH=Maildir
"""

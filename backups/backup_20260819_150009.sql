--
-- PostgreSQL database dump
--

\restrict 6y7g0k7kCLlmnT9c4Y1NLbLD037WerqvnNDOV8Sg6Uvs19Oo3phYOznW9xFaaBW

-- Dumped from database version 14.23 (Ubuntu 14.23-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.23 (Ubuntu 14.23-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_log; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public.activity_log (
    id integer NOT NULL,
    user_id integer,
    action character varying(100),
    details text,
    "timestamp" timestamp without time zone,
    object_type character varying(50),
    object_id integer,
    changes text
);


ALTER TABLE public.activity_log OWNER TO appuser;

--
-- Name: activity_log_id_seq; Type: SEQUENCE; Schema: public; Owner: appuser
--

CREATE SEQUENCE public.activity_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.activity_log_id_seq OWNER TO appuser;

--
-- Name: activity_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: appuser
--

ALTER SEQUENCE public.activity_log_id_seq OWNED BY public.activity_log.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO appuser;

--
-- Name: ip_address; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public.ip_address (
    id integer NOT NULL,
    ip_address character varying(15) NOT NULL,
    subnet_id integer NOT NULL,
    status character varying(20),
    hostname character varying(255),
    mac_address character varying(17),
    device_type character varying(50),
    assigned_to character varying(100),
    description text,
    last_seen timestamp without time zone,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.ip_address OWNER TO appuser;

--
-- Name: ip_address_id_seq; Type: SEQUENCE; Schema: public; Owner: appuser
--

CREATE SEQUENCE public.ip_address_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ip_address_id_seq OWNER TO appuser;

--
-- Name: ip_address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: appuser
--

ALTER SEQUENCE public.ip_address_id_seq OWNED BY public.ip_address.id;


--
-- Name: setting; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public.setting (
    id integer NOT NULL,
    key character varying(100) NOT NULL,
    value character varying(255) NOT NULL
);


ALTER TABLE public.setting OWNER TO appuser;

--
-- Name: setting_id_seq; Type: SEQUENCE; Schema: public; Owner: appuser
--

CREATE SEQUENCE public.setting_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.setting_id_seq OWNER TO appuser;

--
-- Name: setting_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: appuser
--

ALTER SEQUENCE public.setting_id_seq OWNED BY public.setting.id;


--
-- Name: subnet; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public.subnet (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    network_address character varying(18) NOT NULL,
    description text,
    vlan integer,
    location character varying(100),
    gateway character varying(15),
    dns_servers character varying(100),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    alert_threshold integer
);


ALTER TABLE public.subnet OWNER TO appuser;

--
-- Name: subnet_id_seq; Type: SEQUENCE; Schema: public; Owner: appuser
--

CREATE SEQUENCE public.subnet_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subnet_id_seq OWNER TO appuser;

--
-- Name: subnet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: appuser
--

ALTER SEQUENCE public.subnet_id_seq OWNED BY public.subnet.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(64) NOT NULL,
    email character varying(120),
    password_hash character varying(256),
    created_at timestamp without time zone,
    role character varying(20) NOT NULL
);


ALTER TABLE public."user" OWNER TO appuser;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: appuser
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_id_seq OWNER TO appuser;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: appuser
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: webhook; Type: TABLE; Schema: public; Owner: appuser
--

CREATE TABLE public.webhook (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    url character varying(500) NOT NULL,
    event character varying(50) NOT NULL,
    is_active boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.webhook OWNER TO appuser;

--
-- Name: webhook_id_seq; Type: SEQUENCE; Schema: public; Owner: appuser
--

CREATE SEQUENCE public.webhook_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.webhook_id_seq OWNER TO appuser;

--
-- Name: webhook_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: appuser
--

ALTER SEQUENCE public.webhook_id_seq OWNED BY public.webhook.id;


--
-- Name: activity_log id; Type: DEFAULT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.activity_log ALTER COLUMN id SET DEFAULT nextval('public.activity_log_id_seq'::regclass);


--
-- Name: ip_address id; Type: DEFAULT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.ip_address ALTER COLUMN id SET DEFAULT nextval('public.ip_address_id_seq'::regclass);


--
-- Name: setting id; Type: DEFAULT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.setting ALTER COLUMN id SET DEFAULT nextval('public.setting_id_seq'::regclass);


--
-- Name: subnet id; Type: DEFAULT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.subnet ALTER COLUMN id SET DEFAULT nextval('public.subnet_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: webhook id; Type: DEFAULT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.webhook ALTER COLUMN id SET DEFAULT nextval('public.webhook_id_seq'::regclass);


--
-- Data for Name: activity_log; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public.activity_log (id, user_id, action, details, "timestamp", object_type, object_id, changes) FROM stdin;
1	\N	Created subnet LAN	\N	2026-08-10 08:20:31.224706	\N	\N	\N
2	\N	Added IP 192.168.1.254 to LAN	\N	2026-08-10 08:29:52.688032	\N	\N	\N
3	\N	Created subnet WLAN	\N	2026-08-10 08:55:16.777586	\N	\N	\N
4	\N	Added IP 10.11.127.117 to WLAN	\N	2026-08-10 08:56:03.405487	\N	\N	\N
5	\N	CREATE	{"ip": "192.168.1.1", "status": "reserved", "hostname": "", "mac": "", "device_type": "Router", "assigned_to": "MikroTik", "description": ""}	2026-08-11 07:28:05.835933	IPAddress	3	{"ip": "192.168.1.1", "status": "reserved", "hostname": "", "mac": "", "device_type": "Router", "assigned_to": "MikroTik", "description": ""}
6	\N	Added IP 192.168.1.1 to LAN	\N	2026-08-11 07:28:05.846603	\N	\N	\N
7	\N	UPDATE	{"description": {"old": "", "new": "tesss"}}	2026-08-11 07:45:08.716488	IPAddress	3	{"description": {"old": "", "new": "tesss"}}
8	\N	Updated IP 192.168.1.1 in LAN	\N	2026-08-11 07:45:08.727024	\N	\N	\N
9	2	Deleted IP 10.11.127.117	\N	2026-08-14 04:02:29.520712	\N	\N	\N
10	2	DELETE	{"ip": "10.11.127.117", "status": "allocated", "hostname": "", "mac": "", "device_type": "laptop", "assigned_to": "Shared service user", "description": ""}	2026-08-14 04:02:29.527263	IPAddress	2	{"ip": "10.11.127.117", "status": "allocated", "hostname": "", "mac": "", "device_type": "laptop", "assigned_to": "Shared service user", "description": ""}
11	\N	Scanned subnet WLAN: 0 up, 0 down	\N	2026-08-14 08:49:05.694548	\N	\N	\N
12	2	BACKUP	{"file": "backup_20260819_120859.sql"}	2026-08-19 05:08:59.698153	Database	0	{"file": "backup_20260819_120859.sql"}
13	2	DELETE	{"file": "backup_20260819_115448.sql"}	2026-08-19 06:31:36.591111	Backup	0	{"file": "backup_20260819_115448.sql"}
14	2	DELETE	{"file": "backup_20260819_120859.sql"}	2026-08-19 06:31:38.448057	Backup	0	{"file": "backup_20260819_120859.sql"}
15	2	DELETE	{"file": "backup_20260819_115546.sql"}	2026-08-19 06:31:40.513566	Backup	0	{"file": "backup_20260819_115546.sql"}
16	2	BACKUP	{"file": "backup_20260819_133153.sql"}	2026-08-19 06:31:53.97144	Database	0	{"file": "backup_20260819_133153.sql"}
17	2	DELETE	{"file": "backup_20260819_133153.sql"}	2026-08-19 06:36:01.172608	Backup	0	{"file": "backup_20260819_133153.sql"}
18	2	BACKUP	{"file": "backup_20260819_133603.sql"}	2026-08-19 06:36:03.848967	Database	0	{"file": "backup_20260819_133603.sql"}
19	2	DELETE	{"file": "backup_20260819_133603.sql"}	2026-08-19 06:36:18.3709	Backup	0	{"file": "backup_20260819_133603.sql"}
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public.alembic_version (version_num) FROM stdin;
e56d2754c37b
\.


--
-- Data for Name: ip_address; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public.ip_address (id, ip_address, subnet_id, status, hostname, mac_address, device_type, assigned_to, description, last_seen, created_at, updated_at) FROM stdin;
1	192.168.1.254	1	allocated	router.mylab.loc	FC:5C:EE:76:5A:08	Mikrotik	Router	MikroTik Router for internal LAN route and NAT	\N	2026-08-10 08:29:52.674384	2026-08-10 08:29:52.674438
3	192.168.1.1	1	reserved			Router	MikroTik	tesss	\N	2026-08-11 07:28:05.818303	2026-08-11 07:45:08.698608
\.


--
-- Data for Name: setting; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public.setting (id, key, value) FROM stdin;
2	auto_scan_interval	30
1	auto_scan_enabled	false
3	backup_retention_days	7
4	company_logo	/static/uploads/20260819135801_Wikimedia-logo.png
\.


--
-- Data for Name: subnet; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public.subnet (id, name, network_address, description, vlan, location, gateway, dns_servers, created_at, updated_at, alert_threshold) FROM stdin;
1	LAN	192.168.1.0/24	untuk LAN Wired	10	Kantor	192.168.1.254	172.16.1.10	2026-08-10 08:20:31.19923	2026-08-10 08:20:31.19924	\N
2	WLAN	10.11.127.0/24	Wireless subnet IP	2	Office	10.11.127.254	10.202.55.42	2026-08-10 08:55:16.761597	2026-08-10 08:55:16.761607	\N
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public."user" (id, username, email, password_hash, created_at, role) FROM stdin;
2	admin	admin@ipam.local	pbkdf2:sha256:600000$ecW09PIwvR357pcU$dcb85f0be9c7288f0cf21845a74c17c3d1ebfc58191e14dbe9975e96a919aa19	2026-08-11 08:45:34.68366	admin
5	user1	user1@example.com	pbkdf2:sha256:600000$dR9oaS8LfCbqT18K$776931a0ca33e7b6a88c3ed7561e6823ba5a9a2bd6c33eb1cbc0bff0183c9b15	2026-08-17 13:14:56.270256	viewer
\.


--
-- Data for Name: webhook; Type: TABLE DATA; Schema: public; Owner: appuser
--

COPY public.webhook (id, name, url, event, is_active, created_at) FROM stdin;
\.


--
-- Name: activity_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: appuser
--

SELECT pg_catalog.setval('public.activity_log_id_seq', 19, true);


--
-- Name: ip_address_id_seq; Type: SEQUENCE SET; Schema: public; Owner: appuser
--

SELECT pg_catalog.setval('public.ip_address_id_seq', 3, true);


--
-- Name: setting_id_seq; Type: SEQUENCE SET; Schema: public; Owner: appuser
--

SELECT pg_catalog.setval('public.setting_id_seq', 4, true);


--
-- Name: subnet_id_seq; Type: SEQUENCE SET; Schema: public; Owner: appuser
--

SELECT pg_catalog.setval('public.subnet_id_seq', 2, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: appuser
--

SELECT pg_catalog.setval('public.user_id_seq', 5, true);


--
-- Name: webhook_id_seq; Type: SEQUENCE SET; Schema: public; Owner: appuser
--

SELECT pg_catalog.setval('public.webhook_id_seq', 1, false);


--
-- Name: activity_log activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: ip_address ip_address_pkey; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.ip_address
    ADD CONSTRAINT ip_address_pkey PRIMARY KEY (id);


--
-- Name: setting setting_key_key; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.setting
    ADD CONSTRAINT setting_key_key UNIQUE (key);


--
-- Name: setting setting_pkey; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.setting
    ADD CONSTRAINT setting_pkey PRIMARY KEY (id);


--
-- Name: subnet subnet_pkey; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.subnet
    ADD CONSTRAINT subnet_pkey PRIMARY KEY (id);


--
-- Name: ip_address unique_ip_subnet; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.ip_address
    ADD CONSTRAINT unique_ip_subnet UNIQUE (ip_address, subnet_id);


--
-- Name: user user_email_key; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_email_key UNIQUE (email);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: webhook webhook_pkey; Type: CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (id);


--
-- Name: ix_ip_address_ip_address; Type: INDEX; Schema: public; Owner: appuser
--

CREATE INDEX ix_ip_address_ip_address ON public.ip_address USING btree (ip_address);


--
-- Name: ix_user_username; Type: INDEX; Schema: public; Owner: appuser
--

CREATE UNIQUE INDEX ix_user_username ON public."user" USING btree (username);


--
-- Name: activity_log activity_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.activity_log
    ADD CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: ip_address ip_address_subnet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: appuser
--

ALTER TABLE ONLY public.ip_address
    ADD CONSTRAINT ip_address_subnet_id_fkey FOREIGN KEY (subnet_id) REFERENCES public.subnet(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 6y7g0k7kCLlmnT9c4Y1NLbLD037WerqvnNDOV8Sg6Uvs19Oo3phYOznW9xFaaBW


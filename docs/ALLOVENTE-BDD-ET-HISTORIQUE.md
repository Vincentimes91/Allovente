# ALLOVENTE.fr — Base de données complète & historique du travail effectué

Document généré le **2026-11-26** à partir du VPS de production (lecture seule) et des dépôts/historiques disponibles.

**Sources utilisées**
- VPS `vps-1dba3a86` (57.129.153.119), via la passerelle Mistral `allovente-ssh` / `allovente-read-file` (déploiement `allovente-ssh-gateway`) : `information_schema` (tables, colonnes, index), `COUNT(*)` exact par table, `SHOW DATABASES`, `mariadb-dump --no-data`.
- `~/allovente-docs/KNOWLEDGE.md` (export du 06/11/2026), `~/ALLOVENTE-INTERVENTION-20261015.md`, `~/ALLOVENTE-PLAN-CORRECTIONS-20261015.md`.
- Dépôt GitHub `Vincentimes91/Allovente` (4 commits) et historique des exécutions des workflows `allovente-ssh` / `allovente-read-file` (17–21/11/2026).

**Confidentialité** : ce document ne contient aucun mot de passe, aucune clé (SSH/API/DB), aucun secret. Les identifiants de la base (`DB_PASSWORD`, salts WP, clés API) sont volontairement exclus.

---

## 1. Infrastructure

| Élément | Détail |
| --- | --- |
| Serveur | VPS OVH, IPv4 57.129.153.119, hostname `vps-1dba3a86`, Ubuntu 26.04.1 LTS, 6 vCPU, ~11 Go RAM |
| Site | https://allovente.fr — WordPress + WooCommerce, racine `/var/www/allovente` (owner `www-data`), préfixe de tables `wp_` |
| Web | nginx (vhost `/etc/nginx/sites-enabled/allovente.fr`, HSTS, en-têtes sécurité, fastcgi_cache « ALLOVENTE_COHERENT » 6 h, rate-limiting PHP, Brotli activé le 03/11) |
| PHP | PHP 8.5-FPM (pool `www.conf`, `pm.max_children` 24 depuis le 02/11), OPcache `max_accelerated_files` 20000 (03/11) |
| Base de données | **MariaDB 11.8.6**, service `mariadb.service`, écoute en loopback uniquement |
| Cache objets | Redis (`redis-server.service`, loopback) + plugin redis-cache |
| Sécurité | fail2ban actif, SSH par clé ed25519 uniquement (`PasswordAuthentication no` depuis le 03/11), ports exposés 22/80/443 uniquement |
| Passerelle d'admin | service systemd `allovente-gateway` (worker Mistral auto-hébergé sur le VPS, code dans `/home/ubuntu/allovente-gateway/`, port 8089 loopback). Commandes système via `sudo -n` (NOPASSWD) |
| Sauvegardes | Royal Backup (plugin) → fichiers hebdo + base → Google Drive ; surveillance toutes les 10 min (`/opt/allovente-sauvegardes/sauvegardes.sh`) ; disque 2 `/mnt/allovente-data` pour les backups locaux |
| Audits | `/opt/allovente-audit/audit_hebdo.py` (lundi 06:00 UTC, rapport par e-mail) ; rapports dans `/opt/allovente-audit/rapports/` |

**Base de données applicative** (extrait de `wp-config.php`, sans le mot de passe) :
- `DB_NAME` = `wordpress`, `DB_USER` = `admin`, `DB_HOST` = `localhost`, `$table_prefix` = `wp_`
- Bases présentes sur le serveur : `wordpress` + les bases système (`information_schema`, `mysql`, `performance_schema`, `sys`). La base de staging `allovente_stage_20261015` (1,6 Go) a été supprimée le 03/11/2026.

---

## 2. Passerelle Mistral Workflows (dépôt `Vincentimes91/Allovente`)

Deux workflows exposés, servis par le déploiement `allovente-ssh-gateway` (worker auto-hébergé sur le VPS depuis le 02/11/2026) :

| Workflow | Entrée | Rôle |
| --- | --- | --- |
| `allovente-ssh` | `{"command": "...", "timeout_seconds": 120}` | Exécute une commande shell sur le VPS (subprocess local, `cwd=/home/ubuntu`) |
| `allovente-read-file` | `{"path": "/...", "max_bytes": 500000}` | Lit un fichier du VPS |

Sortie commune : `{"exit_code", "stdout", "stderr", "timed_out", "error"}` (stdout tronqué à 200 000 caractères).

Historique du dépôt (branche `main`) :
1. `a81b124` — Initial commit
2. `e3a8b89` — Passerelle SSH vers le VPS (clé privée via secret de workspace `allovente_ssh_key`, host key épinglée, `RejectPolicy`)
3. `337c1e1` — Worker auto-hébergé sur le VPS : exécution locale via subprocess (plus de SSH/clé), setup systemd
4. `4b3e065` — `setup.sh` : ajout de `DEPLOYMENT_NAME` requis au démarrage du worker

Fichiers : `worker.py` + `ssh_exec.py` (variante managed, avec clé SSH), `selfhosted/` (`worker.py`, `cmd_exec.py`, `setup.sh`, `allovente-gateway.service`), `Dockerfile`, `requirements.txt` (`mistralai-workflows>=3.10`, `paramiko>=3.5`).

Utilisation depuis Vibe : `execute_workflow({workflow_identifier: "allovente-ssh", input: {command: "..."}})` puis `get_workflow_execution(execution_id)`. Aucun identifiant nécessaire côté client. Pièges connus : la passerelle exécute `sh` (pas de heredoc fiable — envoyer les patchs Python en base64), les commandes root passent par `sudo -n`.

---

## 3. Base de données `wordpress` — vue d'ensemble (2026-11-26)

- **Moteur** : MariaDB 11.8.6, 100 % InnoDB
- **Taille** : ≈ 2,6 Go (données + index)
- **Tables** : **139**
- Répartition : 12 tables cœur WordPress, 35 tables WooCommerce (`wp_wc_*` / `wp_woocommerce_*`), 88 tables de plugins tiers, **4 tables maison Allovente**
- Tables maison : `wp_akd_catalog`, `wp_akd_orders`, `wp_allovente_myfusion_catalogue`, `wp_allovente_sales_funnel`

### Chiffres clés

| Indicateur | Valeur |
| --- | ---: |
| `wp_posts` (total) | 403 065 |
| — produits publiés | 47 802 |
| — produits brouillons | 1 163 |
| — variations de produits | 4 158 (publish 4 137 + private 21) |
| — pièces jointes (médias) | 349 406 |
| — pages publiées | 25 |
| `wp_postmeta` | 3 628 250 |
| `wp_options` | 9 815 |
| `wp_users` / `wp_usermeta` | 15 / 698 |
| `wp_wc_orders` (commandes HPOS) | 31 |
| `wp_woocommerce_order_items` | 82 |
| `wp_actionscheduler_actions` / `_logs` | 236 881 / 710 683 |
| `wp_allovente_myfusion_catalogue` (catalogue importé) | 176 342 |
| `wp_gla_merchant_issues` (Google Merchant) | 10 518 |
| `wp_terms` / `wp_term_taxonomy` | 1 665 |
| `wp_independent_analytics_views` / `sessions` | 13 151 / 3 034 |

Répartition `wp_posts` par type/statut :

```
attachment inherit 349406 | custom_css publish 1 | e_global_class publish 2 | elementor_library publish 2
forminator_forms publish 1 | nav_menu_item publish 3 | page publish 25 | page trash 1 | post auto-draft 1
product draft 1163 | product publish 47802 | product trash 266 | product_variation private 21
product_variation publish 4137 | product_variation trash 46 | revision inherit 67 | shop_coupon publish 4
shop_coupon trash 1 | shop_order_placehold draft 31 | wp_font_face publish 36 | wp_font_family publish 12
wp_global_styles publish 1 | wp_navigation publish 1 | wpcode draft 4 | wpcode publish 27 | wpr_templates publish 4
```

### Inventaire complet des 139 tables (lignes = COUNT(*) exact, taille = data+index en Mo)

| Table | Lignes | Mo | Catégorie |
| --- | ---: | ---: | --- |
| wp_actionscheduler_actions | 236881 | 194.59 | Plugin tiers (Action Scheduler) |
| wp_actionscheduler_claims | 46 | 0.03 | Plugin tiers |
| wp_actionscheduler_groups | 22 | 0.03 | Plugin tiers |
| wp_actionscheduler_logs | 710683 | 100.20 | Plugin tiers |
| wp_akd_catalog | 0 | 0.03 | **Maison Allovente** |
| wp_akd_orders | 0 | 0.03 | **Maison Allovente** |
| wp_allovente_myfusion_catalogue | 176342 | 135.23 | **Maison Allovente** |
| wp_allovente_sales_funnel | 81 | 0.02 | **Maison Allovente** |
| wp_cmplz_cookiebanners | 1 | 0.02 | Plugin tiers (Complianz) |
| wp_cmplz_cookies | 128 | 0.05 | Plugin tiers |
| wp_cmplz_dnsmpd | 0 | 0.02 | Plugin tiers |
| wp_cmplz_services | 20 | 0.02 | Plugin tiers |
| wp_commentmeta | 207 | 0.05 | Core WP |
| wp_comments | 279 | 0.20 | Core WP |
| wp_e_events | 0 | 0.03 | Plugin tiers |
| wp_frmt_form_entry | 5 | 0.11 | Plugin tiers (Forminator) |
| wp_frmt_form_entry_meta | 35 | 0.06 | Plugin tiers |
| wp_frmt_form_reports | 1 | 0.02 | Plugin tiers |
| wp_frmt_form_views | 67 | 0.08 | Plugin tiers |
| wp_fsmpt_email_logs | 126 | 4.03 | Plugin tiers (FluentSMTP) |
| wp_gla_attribute_mapping_rules | 0 | 0.02 | Plugin tiers (Google Listings & Ads) |
| wp_gla_budget_recommendations | 4230 | 0.33 | Plugin tiers |
| wp_gla_merchant_issues | 10518 | 3.52 | Plugin tiers |
| wp_gla_merchant_price_benchmarks | 999 | 0.27 | Plugin tiers |
| wp_gla_shipping_rates | 1 | 0.05 | Plugin tiers |
| wp_gla_shipping_times | 1 | 0.03 | Plugin tiers |
| wp_independent_analytics_campaigns | 0 | 0.09 | Plugin tiers (Independent Analytics) |
| wp_independent_analytics_campaign_urls | 0 | 0.03 | Plugin tiers |
| wp_independent_analytics_cities | 822 | 0.11 | Plugin tiers |
| wp_independent_analytics_clicked_links | 0 | 0.05 | Plugin tiers |
| wp_independent_analytics_clicks | 0 | 0.05 | Plugin tiers |
| wp_independent_analytics_click_targets | 0 | 0.02 | Plugin tiers |
| wp_independent_analytics_countries | 44 | 0.03 | Plugin tiers |
| wp_independent_analytics_device_browsers | 11 | 0.03 | Plugin tiers |
| wp_independent_analytics_device_oss | 7 | 0.03 | Plugin tiers |
| wp_independent_analytics_device_types | 3 | 0.03 | Plugin tiers |
| wp_independent_analytics_forms | 1 | 0.03 | Plugin tiers |
| wp_independent_analytics_form_submissions | 5 | 0.02 | Plugin tiers |
| wp_independent_analytics_landing_pages | 0 | 0.02 | Plugin tiers |
| wp_independent_analytics_links | 0 | 0.06 | Plugin tiers |
| wp_independent_analytics_link_rules | 4 | 0.02 | Plugin tiers |
| wp_independent_analytics_orders | 18 | 0.14 | Plugin tiers |
| wp_independent_analytics_referrers | 22 | 0.06 | Plugin tiers |
| wp_independent_analytics_referrer_types | 5 | 0.03 | Plugin tiers |
| wp_independent_analytics_reports | 20 | 0.03 | Plugin tiers |
| wp_independent_analytics_resources | 6340 | 1.67 | Plugin tiers |
| wp_independent_analytics_sessions | 3034 | 2.44 | Plugin tiers |
| wp_independent_analytics_utm_campaigns | 0 | 0.02 | Plugin tiers |
| wp_independent_analytics_utm_mediums | 0 | 0.02 | Plugin tiers |
| wp_independent_analytics_utm_sources | 0 | 0.02 | Plugin tiers |
| wp_independent_analytics_views | 13151 | 4.55 | Plugin tiers |
| wp_independent_analytics_visitors | 2095 | 0.28 | Plugin tiers |
| wp_independent_analytics_wc_orders | 0 | 0.08 | Plugin tiers |
| wp_keybin_logs | 0 | 0.02 | Plugin maison (keybin-fr) |
| wp_links | 0 | 0.03 | Core WP |
| wp_mwai_filemeta | 0 | 0.02 | Plugin tiers (Meow AI) |
| wp_mwai_files | 0 | 0.03 | Plugin tiers |
| wp_mwai_tasklogs | 0 | 0.03 | Plugin tiers |
| wp_mwai_tasks | 4 | 0.08 | Plugin tiers |
| wp_options | 9815 | 52.75 | Core WP |
| wp_packlink_entity | 3 | 0.02 | Plugin tiers |
| wp_pmxi_files | 0 | 0.02 | Plugin tiers (WP All Import) |
| wp_pmxi_hash | 0 | 0.02 | Plugin tiers |
| wp_pmxi_history | 0 | 0.02 | Plugin tiers |
| wp_pmxi_images | 307 | 0.02 | Plugin tiers |
| wp_pmxi_imports | 0 | 0.02 | Plugin tiers |
| wp_pmxi_posts | 0 | 0.02 | Plugin tiers |
| wp_pmxi_templates | 0 | 0.02 | Plugin tiers |
| wp_postmeta | 3628250 | 1696.83 | Core WP |
| wp_posts | 403065 | 400.73 | Core WP |
| wp_rank_math_analytics_gsc | 1080 | 0.45 | Plugin tiers (Rank Math) |
| wp_rank_math_analytics_inspections | 266 | 0.23 | Plugin tiers |
| wp_rank_math_analytics_objects | 23247 | 8.03 | Plugin tiers |
| wp_rank_math_internal_links | 672 | 0.17 | Plugin tiers |
| wp_rank_math_internal_meta | 71544 | 3.52 | Plugin tiers |
| wp_redirection_404 | 1 | 0.06 | Plugin tiers (Redirection) |
| wp_redirection_groups | 2 | 0.05 | Plugin tiers |
| wp_redirection_items | 0 | 0.11 | Plugin tiers |
| wp_redirection_logs | 93 | 0.11 | Plugin tiers |
| wp_snippets | 5 | 0.05 | Plugin tiers (WPCode) |
| wp_srfm_entries | 0 | 0.06 | Plugin tiers |
| wp_srfm_payments | 0 | 0.02 | Plugin tiers |
| wp_surecart_incoming_webhooks | 0 | 0.08 | Plugin tiers (SureCart) |
| wp_surecart_integrations | 0 | 0.08 | Plugin tiers |
| wp_surecart_variant_option_values | 11 | 0.13 | Plugin tiers |
| wp_surecookie_consent_log | 4 | 0.13 | Plugin tiers |
| wp_suretriggers_webhook_requests | 0 | 0.02 | Plugin tiers |
| wp_termmeta | 626 | 0.13 | Core WP |
| wp_terms | 1665 | 0.28 | Core WP |
| wp_term_relationships | 232918 | 23.08 | Core WP |
| wp_term_taxonomy | 1665 | 0.34 | Core WP |
| wp_trp_dictionary_fr_fr_en_us | 144 | 0.13 | Plugin tiers (TranslatePress) |
| wp_trp_gettext_en_us | 6 | 0.09 | Plugin tiers |
| wp_trp_gettext_fr_fr | 6462 | 2.39 | Plugin tiers |
| wp_trp_gettext_original_meta | 0 | 0.06 | Plugin tiers |
| wp_trp_gettext_original_strings | 6461 | 3.92 | Plugin tiers |
| wp_trp_original_meta | 0 | 0.06 | Plugin tiers |
| wp_trp_original_strings | 141 | 0.03 | Plugin tiers |
| wp_usermeta | 698 | 0.16 | Core WP |
| wp_users | 15 | 0.06 | Core WP |
| wp_wcpdf_invoice_number | 19 | 0.03 | Plugin tiers (PDF Invoices) |
| wp_wcpdf_packing_slip_number | 0 | 0.03 | Plugin tiers |
| wp_wc_admin_notes | 83 | 0.06 | WooCommerce |
| wp_wc_admin_note_actions | 111 | 0.08 | WooCommerce |
| wp_wc_category_lookup | 305 | 0.02 | WooCommerce |
| wp_wc_customer_lookup | 14 | 0.05 | WooCommerce |
| wp_wc_download_log | 0 | 0.05 | WooCommerce |
| wp_wc_orders | 31 | 0.16 | WooCommerce (HPOS) |
| wp_wc_orders_meta | 1052 | 1.75 | WooCommerce |
| wp_wc_order_addresses | 34 | 0.08 | WooCommerce |
| wp_wc_order_coupon_lookup | 5 | 0.05 | WooCommerce |
| wp_wc_order_operational_data | 31 | 0.05 | WooCommerce |
| wp_wc_order_product_lookup | 42 | 0.09 | WooCommerce |
| wp_wc_order_stats | 31 | 0.09 | WooCommerce |
| wp_wc_order_tax_lookup | 31 | 0.05 | WooCommerce |
| wp_wc_product_attributes_lookup | 4056 | 0.98 | WooCommerce |
| wp_wc_product_download_directories | 2 | 0.03 | WooCommerce |
| wp_wc_product_meta_lookup | 53480 | 22.03 | WooCommerce |
| wp_wc_rate_limits | 0 | 0.03 | WooCommerce |
| wp_wc_reserved_stock | 0 | 0.03 | WooCommerce |
| wp_wc_stock_notificationmeta | 0 | 0.05 | WooCommerce |
| wp_wc_stock_notifications | 0 | 0.06 | WooCommerce |
| wp_wc_tax_rate_classes | 2 | 0.03 | WooCommerce |
| wp_wc_webhooks | 5 | 0.03 | WooCommerce |
| wp_woocommerce_api_keys | 3 | 0.05 | WooCommerce |
| wp_woocommerce_attribute_taxonomies | 19 | 0.03 | WooCommerce |
| wp_woocommerce_downloadable_product_permissions | 0 | 0.09 | WooCommerce |
| wp_woocommerce_log | 0 | 0.03 | WooCommerce |
| wp_woocommerce_order_itemmeta | 767 | 0.17 | WooCommerce |
| wp_woocommerce_order_items | 82 | 0.03 | WooCommerce |
| wp_woocommerce_payment_tokenmeta | 6 | 0.05 | WooCommerce |
| wp_woocommerce_payment_tokens | 1 | 0.03 | WooCommerce |
| wp_woocommerce_sessions | 153 | 1.06 | WooCommerce |
| wp_woocommerce_shipping_zones | 1 | 0.03 | WooCommerce |
| wp_woocommerce_shipping_zone_locations | 1 | 0.05 | WooCommerce |
| wp_woocommerce_shipping_zone_methods | 2 | 0.05 | WooCommerce |
| wp_woocommerce_tax_rates | 1 | 0.08 | WooCommerce |
| wp_woocommerce_tax_rate_locations | 0 | 0.05 | WooCommerce |
| wp_wpvivid_options | 0 | 0.03 | Plugin tiers (Royal Backup) |

---

## 4. Détail des tables principales

### 4.1 Tables maison Allovente

**`wp_akd_catalog`** (0 ligne) — catalogue fournisseur (Kinguin/« akd ») en cache local :

| Colonne | Type | Null | Clé | Extra |
| --- | --- | --- | --- | --- |
| id | bigint(20) unsigned | NO | PRI | auto_increment |
| sku | varchar(191) | NO | UNI | |
| payload | longtext | NO | | |
| generation | varchar(36) | NO | | |
| wc_id | bigint(20) unsigned | NO | | |
| fetched_at | bigint(20) unsigned | NO | | |

**`wp_akd_orders`** (0 ligne) — suivi des commandes chez le fournisseur :

| Colonne | Type | Null | Clé | Extra |
| --- | --- | --- | --- | --- |
| wc_id | bigint(20) unsigned | NO | PRI | |
| external_id | varchar(191) | NO | UNI | |
| order_id | bigint(20) unsigned | NO | | |
| state | varchar(32) | NO | | |
| supplier_status | varchar(64) | NO | | |
| updated_at | bigint(20) unsigned | NO | | |

**`wp_allovente_myfusion_catalogue`** (176 342 lignes, 135 Mo) — catalogue fusionné (plugin maison myfusion-catalogue) :

| Colonne | Type | Null | Clé | Extra |
| --- | --- | --- | --- | --- |
| product_id | bigint(20) unsigned | NO | PRI | |
| name | text | NO | | |
| sku | varchar(191) | NO | | |
| ean | varchar(64) | NO | | |
| category_name | varchar(191) | NO | MUL | |
| brand_name | varchar(191) | NO | MUL | |
| price | decimal(18,6) | YES | | |
| quantity | bigint(20) | YES | | |
| payload | longtext | NO | | |
| selected | tinyint(4) | NO | MUL | |
| target_category | bigint(20) unsigned | NO | | |
| wc_id | bigint(20) unsigned | NO | | |
| import_state | varchar(20) | NO | | |
| import_error | text | YES | | |
| details | longtext | YES | | |
| import_settings | longtext | YES | | |
| seen_at | datetime | NO | | |

**`wp_allovente_sales_funnel`** (81 lignes) — entonnoir de vente agrégé par jour/événement/device (PK composite `event_day,event_name,device`) :

| Colonne | Type | Null | Clé |
| --- | --- | --- | --- |
| event_day | date | NO | PRI |
| event_name | varchar(32) | NO | PRI |
| device | varchar(10) | NO | PRI |
| total | bigint(20) unsigned | NO | |

### 4.2 Cœur WordPress

**`wp_posts`** (403 065 lignes) : `ID` (PRI, auto_increment), `post_author` (MUL), `post_date`, `post_date_gmt`, `post_content` longtext, `post_title` text, `post_excerpt`, `post_status`, `comment_status`, `ping_status`, `post_password`, `post_name` (MUL), `to_ping`, `pinged`, `post_modified`, `post_modified_gmt`, `post_content_filtered`, `post_parent` (MUL), `guid`, `menu_order`, `post_type` (MUL), `post_mime_type`, `comment_count`. Index : `type_status_author`, `type_status_date`.

**`wp_postmeta`** (3 628 250 lignes, 1,7 Go — la plus grosse table) : `meta_id` (PRI), `post_id` (MUL), `meta_key` (MUL), `meta_value` longtext. **Index maison additionnel** : `allovente_key_value (meta_key, meta_value)`.

**`wp_options`** (9 815) : `option_id` (PRI), `option_name` (UNI), `option_value` longtext, `autoload` (MUL).

**`wp_users`** (15) : `ID` (PRI), `user_login` (MUL), `user_pass`, `user_nicename` (MUL), `user_email` (MUL), `user_url`, `user_registered`, `user_activation_key`, `user_status`, `display_name`.
**`wp_usermeta`** (698) : `umeta_id` (PRI), `user_id` (MUL), `meta_key` (MUL), `meta_value` longtext.
**`wp_terms` / `wp_term_taxonomy` / `wp_term_relationships` / `wp_termmeta`** : taxonomies standards (1 665 termes, 232 918 relations).

### 4.3 WooCommerce (sélection)

**`wp_wc_orders`** (31 commandes, stockage HPOS) : `id` (PRI), `status` (MUL), `currency`, `type` (MUL), `tax_amount`, `total_amount` decimal(26,8), `customer_id` (MUL), `billing_email` (MUL), `date_created_gmt` (MUL), `date_updated_gmt`, `parent_order_id` (MUL), `payment_method`, `payment_method_title`, `transaction_id` (MUL), `ip_address`, `user_agent`, `customer_note`. Index : `type_status_date`, `customer_id_status`, `customer_id_billing_email`, `date_created`, `date_updated`.

**`wp_wc_order_product_lookup`** (42) : `order_item_id`+`order_id` (PRI), `product_id` (MUL), `variation_id`, `customer_id` (MUL), `date_created` (MUL), `product_qty`, `product_net_revenue`, `product_gross_revenue`, `coupon_amount`, `tax_amount`, `shipping_amount`, `shipping_tax_amount`. Index : `customer_product_date`.

Tables lookup associées : `wp_wc_order_stats`, `wp_wc_order_addresses`, `wp_wc_order_tax_lookup`, `wp_wc_order_coupon_lookup`, `wp_wc_order_operational_data` (dont `order_key` MUL), `wp_wc_orders_meta`, `wp_woocommerce_order_items` (82) + `wp_woocommerce_order_itemmeta` (767), `wp_wc_product_meta_lookup` (53 480 : sku MUL, prix min/max, stock, ventes…), `wp_wc_product_attributes_lookup`, `wp_wc_category_lookup`, `wp_wc_customer_lookup`, `wp_woocommerce_sessions` (153), `wp_wc_webhooks` (5), `wp_woocommerce_api_keys` (3).

### 4.4 Métadonnées métier `wp_postmeta` (recensement du 20/11/2026)

| Meta key | Lignes | Rôle |
| --- | ---: | --- |
| `_kinguin_product_id`, `_kinguin_id`, `_kinguin_price`, `_kinguin_rule`, `_kinguin_steam_price`, `_kinguin_preorder`, `_kinguin_synced` | 44 214 chacune | données sync Kinguin (prix, stock, règles) |
| `_allovente_transport_cost_ht` | 5 083 | coûts transport |
| `_allovente_supplier_cost_ht`, `_allovente_purchase_cost_ht_shipping` | 4 982 | coût fournisseur / achat |
| `_prix_achat_ht` | 4 638 | prix d'achat HT (legacy) |
| `_allovente_cost_source` | 4 156 | source du coût |
| `_av_at_cost_approved` | 1 017 | prix au coût approuvé |
| `_av_sunsky_pc_initial_import_price_eur`, `_av_sunsky_pc_received_price_basis` | 400 | prix Sunsky (import vs reçu) |
| `_av_at_cost_fee_percent`, `_av_at_cost_fee_fixed` | 210 | frais au coût |
| `_av_sunsky_pricing_state` | 52 | état pricing Sunsky |
| `_allovente_kinguin_tr_fail` | 44 | échecs de traduction Kinguin |
| `_av_sunsky_cost_basis`, `_av_sunsky_import_cost_eur`, `_av_sunsky_cost_received_at` | 42 | base de coût Sunsky |
| `_av_sunsky_approved_candidate_price_ttc` | 2 | candidat approuvé TTC |
| `_av_kinguin_remap_note` | 1 | note de remapping |

Convention de nommage des titres (confirmée en base) : « Nom du jeu – DLC – Clé Steam », « Nom – Clé Xbox One / Series X|S (Europe) » — les noms commerciaux restent en anglais, seuls les suffixes génériques sont francisés (règle du 05/11).

---

## 5. Historique de ce qui a été fait pour allovente.fr

Chronologie reconstituée depuis `~/allovente-docs/KNOWLEDGE.md`, les rapports d'intervention du 15/10, l'historique git du dépôt et les exécutions des workflows (toutes les actions ci-dessous ont été réalisées avec l'accord de Vincent, sauf mention contraire).

### 15 octobre 2026 — sécurité, sauvegardes, audit Google/SEO
- **Durcissement nginx** : refus 403 de l'exécution PHP dans `/wp-content/uploads|upgrade|cache`, blocage de `wc-logs`, des exports CSV sensibles et des dossiers de sauvegarde (Royal Backup) ; `nginx -t` puis reload, tests 403 OK. Configs précédentes conservées dans `/home/ubuntu`.
- **Sauvegardes** : dump SQL sur disque secondaire (`/mnt/allovente-data/backups/allovente/safety-20261015/`, gzip + SHA256 vérifié) ; archive site 36 Go (`site-files-20261015.tar.zst`, SHA256 + `zstd -t` OK) ; test de restauration dans une base temporaire.
- **Préproduction** : copie `/home/ubuntu/allovente-staging-20261015` + base `allovente_stage_20261015` (116 311 posts), URL interne 127.0.0.1:8765, cron désactivé (supprimées depuis, voir 03/11).
- **Mises à jour** de 4 plugins testées en préprod puis appliquées en prod via WP-CLI (`www-data`) : Google Listings & Ads 3.9.6, Complianz 7.5.6, WooCommerce Services 3.7.3, Elementor 4.3.5 (erreur fatale transitoire Black_Friday résolue par reload php-fpm).
- **Google Merchant / GLA** : cause racine des 3 265 actions `update_products` en échec = produits `_wc_gla_visibility='dont-sync-and-show'` exclus de la synchro mais recevant quand même des actions (« Job item not found »). 33 498 produits Jeux vidéo + 5 014 Accessoires. 431 signalements `image_link_internal_error` côté Google alors que les images répondent 200 en local (non reproductible côté serveur).
- **SEO** : descriptions éditoriales + métadonnées Rank Math sur 4 catégories smartphones (Asus, Blackview, OnePlus, Vivo) ; purge ciblée du cache FastCGI ; audit des 195 sous-sitemaps (25 584 entrées → 25 926 URL uniques après invalidation du cache Rank Math, 132 doublons résiduels) ; Search Console `sc-domain:allovente.fr` connecté, sitemap soumis.

### 2 novembre 2026 — passerelle Mistral + maintenance système
- **Passerelle permanente installée** : dépôt GitHub `Vincentimes91/Allovente`, déploiement `allovente-ssh-gateway` (voir §2 et commits plus haut). Test `uptime` OK en 1,5 s.
- **20 mises à jour système** appliquées (kernel 7.0.0-42, systemd 259.9, ubuntu-pro) + reboot à 00:03 CET ; tous les services OK.
- **Audit hebdomadaire automatisé** : `/opt/allovente-audit/audit_hebdo.py`, lundi 06:00 UTC, rapport par e-mail.
- Incident Kinguin #213918 (clés récupérées) et export de base local désactivé le 31/10 au profit de Royal Backup → Google Drive : résolus/validés.

### 3 novembre 2026 — nettoyage, incident uniformisation, sécurité
- **Base staging supprimée** (`allovente_stage_20261015`, 1,6 Go, droppée après vérification d'absence de références).
- **Nettoyage fichiers** : ~8,5 Go libérés (dumps, tests, caches, anciens dossiers). ⚠️ Un module `/home/ubuntu/uniformisation/` (fiche.py + seo.py, importé par les imports Kinguin et TechTablet) a été supprimé par erreur → **incident** : échecs des syncs 05-06h. **Restauration par rétro-ingénierie** à partir de fiches réelles en base ; sortie validée identique au caractère près ; relances Kinguin/TechTablet OK (0 erreur).
- **App mobile supprimée** (service `allovente-vps`, port 8090 HTTP non TLS) : service arrêté, unit supprimé, règles UFW retirées, code archivé.
- **SSH verrouillé** : clé ed25519 installée, `PasswordAuthentication no` (le coupable était `50-cloud-init.conf`), ancien mot de passe rotaté.
- **Outils IA/MCP supprimés** (desktop-commander, Gemini CLI, claude-server) — seule la passerelle Mistral est conservée.
- **Performance** : cache-warmer corrigé `40 * * * *` → `*/15 * * * *` ; **Brotli** activé sur nginx ; **OPcache** 10000 → 20000 ; journald vacuum 360→64 Mo + plafond 100M.
- **Prix Sunsky** : mu-plugin `allovente-sunsky-pricing.php` — arrondis psychologiques .49/.99 toutes les 30 min.

### 4 novembre 2026 — performance (purges, warmer, slowlogs) + UX
- **purge-all v2** (`/usr/local/lib/allovente/nginx-purge-all.php`) : 1 requête par clé au lieu de 6 (la clé de cache nginx ne varie pas selon Accept-Encoding) → **~53 000 → ~3 000 purges** par passage de sync Kinguin (division par ~18).
- **cache-warmer v2** (`/home/ubuntu/cache-warmer/warm.sh`) : 1 seule requête/URL, pacing, mode `light` (*/15) + `full` (7h) → ~500 req/h au lieu de ~6 000.
- **Slowlogs activés** (PHP-FPM 2 s puis remis à 10 s ; MariaDB `long_query_time=3`) : les requêtes lentes (>3 s) sont les grilles boutique Royal Elementor (`wpr-woo-grid`) pendant les syncs Kinguin (REGEXP sur `post_title`, CAST sur `meta_value` → non indexables). Décision : **aucun index ajouté** (pages cachées nginx côté visiteurs).
- **Scan Complianz neutralisé** (option `cmplz_wsc_status` → disabled) : le websitescan (sleep 6 s × 25 itérations) retenait un worker PHP.
- **Corrections UX** : filtres catalogue auto-apply (`allovente-game-filters.php` v1.7.0), filtre console « PC/Steam », bloc avis traduit (« Aucun avis — soyez le premier… »), via mu-plugin `allovente-ux-polish.php`.
- **Diagnostic traduction** : ~60-65 % des titres restaient en EN (« … CD Key ») — cause identifiée le 05/11.

### 5 novembre 2026 — traduction, titres, nettoyage plugins, audit
- **`rattrapage.php` recréé (v2.1)** dans `/home/ubuntu/translation-auto/` (appelé par `daily_sync.sh`) + patch du plugin `allovente-keybin-fr` (`is_translation_candidate()` reconnaît « cd key »/« language only »).
- **Campagne de traduction massive** lancée puis **arrêtée ~06h45** (12 workers → saturation CPU + 3,87 M requêtes de purge inutiles la nuit du 04-05/11).
- **Mystère des titres résolu** : aucun réécrivain — OpenAI renvoyait le titre inchangé (prompt « DONNÉES À PROTÉGER »), et le mu-plugin `allovente-product-names-fr.php` masquait le vrai état via le filtre `the_title`.
- **Normalisation massive en base** (`normalize-titres.php`) : **35 284 titres** normalisés (« Nom – Clé Steam »), puis 64 → **0** titres « CD Key » résiduels. Patchs keybin + product-names-fr pour les futurs imports.
- **Nettoyage plugins** : plugin inactif `maintenance` supprimé, 5 mu-plugins obsolètes archivés dans `/home/ubuntu/plugins-retires/`, 30 plugins actifs conservés (tous justifiés).
- **Audit hebdo** : destinataires étendus à 3 adresses (jusqu'au 20/12/2026 inclus, retrait planifié via tâche Vibe).
- **Mystère wp-cron résolu** : `DISABLE_WP_CRON=true` mais les événements tournent 1×/jour à 15h20 via le ping de `/home/ubuntu/catalog-ranking/rank.py` (ligne 77).
- **Audit complet du serveur** (lecture seule) : serveur sain (load 1,49/6, RAM 3,1/11 Go, 0 erreur 5xx/24h, TTFB accueil 0,05 s, Redis ~87 % hit, TLS 1.2/1.3), 1 seul admin, fail2ban actif. Projet fournisseur **1fotrade abandonné** (photos filigranées) et intégralement nettoyé.

### 6 novembre 2026 — incident sync Kinguin
- Échec du full 06h : réponse API Kinguin tronquée (JSON incomplet) page ~1000 → **retry ×6 (backoff 2^n)** ajouté à `fetch_catalog.py` et `incremental_fetch.py` (backups `.bak-20261106`) ; relance manuelle OK.

### 17–21 novembre 2026 — opérations récentes (via la passerelle)
- **17/11** : vérification accessibilité images — 15 fiches testées, 120 images, **0 sans attribut alt**.
- **19/11** : **politique de mot de passe** — mu-plugin `allovente-password-policy.php` (8 caractères min, majuscule, chiffre, caractère spécial ; options WooCommerce `woocommerce_registration_generate_password`, `woocommerce_min_password_strength` mises à jour) ; audit de la liste des mu-plugins (~40 fichiers actifs + backups).
- **20/11** : recensement des métadonnées `wp_postmeta` métier (voir §4.4 — prix/coûts Kinguin et Sunsky).
- **21/11** : séries de commandes de vérification sur le VPS (état général OK).

### En continu (automatismes en place)
- Syncs fournisseurs : **Kinguin** (full 06h/14h/22h + intraday prix/stock 08h/14h/20h, via systemd timers, ~1 h pour le full du matin) ; **TechTablet** import 7h15-10h15 avec flock.
- Cron métier : rapport anomalies 7h40, audit catalogue 7h50, homepage-auto 15h, catalog-ranking 15h20 (+ fix_categories, release_dates), CSS critique 2h15/13h15, demandes d'avis 8h05, réservoirs « vous aimerez aussi » toutes les 6 h, cache-warmer */15 + full 7h, audit hebdo lundi 6h, arrondis Sunsky toutes les 30 min, images manquantes (fill-images.php 4h40, 300 fiches/nuit).
- ~80 mu-plugins maison dans `wp-content/mu-plugins/` (SEO, perf, UX/branding, métier prix/stock, acquisition, PWA, sécurité…), 31 plugins actifs.

### Règles et contraintes actées
- **Aucune modification visuelle du site** sans accord explicite.
- **Trackers Meta (Pixel + CAPI) et Google doivent toujours se charger** (campagnes Ads actives) — jamais gatés derrière le consentement. Conséquence connue : la home répond `MISS` au cache nginx à cause du `Set-Cookie: _fbp` serveur (servie en <10 ms quand même).
- **Ne jamais toucher aux plugins/API des fournisseurs** (Kinguin, TechTablet) qui synchronisent les produits.
- Noms commerciaux des jeux en anglais ; seuls les suffixes génériques sont francisés.
- Toute modification : **backup `.bak-*` d'abord**, purge du cache nginx après, vérif HTTP 200 ; commandes root via `sudo -n` ; patchs Python envoyés en base64 (la passerelle exécute `sh`).
- Ne jamais exposer le VPS ni les services du sandbox publiquement.

---

## 6. Annexe A — Schéma complet : toutes les colonnes (1 161 lignes)

Export brut `information_schema.COLUMNS` (base `wordpress`, 2026-11-26), trié par table puis position.
Format : `table | colonne | type | null | clé | extra` (PRI = primaire, UNI = unique, MUL = indexée).
Le dump DDL complet (`CREATE TABLE`) est disponible sur le VPS : `/home/ubuntu/allovente-db-schema.sql` (`mariadb-dump --no-data --skip-comments --compact wordpress`, 108 873 octets).

```
wp_actionscheduler_actions | action_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_actionscheduler_actions | hook | varchar(191) | NO | MUL |
wp_actionscheduler_actions | status | varchar(20) | NO | MUL |
wp_actionscheduler_actions | scheduled_date_gmt | datetime | YES | MUL |
wp_actionscheduler_actions | scheduled_date_local | datetime | YES | |
wp_actionscheduler_actions | priority | tinyint(3) unsigned | NO | |
wp_actionscheduler_actions | args | varchar(191) | YES | MUL |
wp_actionscheduler_actions | schedule | longtext | YES | |
wp_actionscheduler_actions | group_id | bigint(20) unsigned | NO | MUL |
wp_actionscheduler_actions | attempts | int(11) | NO | |
wp_actionscheduler_actions | last_attempt_gmt | datetime | YES | MUL |
wp_actionscheduler_actions | last_attempt_local | datetime | YES | |
wp_actionscheduler_actions | claim_id | bigint(20) unsigned | NO | MUL |
wp_actionscheduler_actions | extended_args | varchar(8000) | YES | |
wp_actionscheduler_claims | claim_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_actionscheduler_claims | date_created_gmt | datetime | YES | MUL |
wp_actionscheduler_groups | group_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_actionscheduler_groups | slug | varchar(255) | NO | MUL |
wp_actionscheduler_logs | log_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_actionscheduler_logs | action_id | bigint(20) unsigned | NO | MUL |
wp_actionscheduler_logs | message | text | NO | |
wp_actionscheduler_logs | log_date_gmt | datetime | YES | MUL |
wp_actionscheduler_logs | log_date_local | datetime | YES | |
wp_akd_catalog | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_akd_catalog | sku | varchar(191) | NO | UNI |
wp_akd_catalog | payload | longtext | NO | |
wp_akd_catalog | generation | varchar(36) | NO | |
wp_akd_catalog | wc_id | bigint(20) unsigned | NO | |
wp_akd_catalog | fetched_at | bigint(20) unsigned | NO | |
wp_akd_orders | wc_id | bigint(20) unsigned | NO | PRI |
wp_akd_orders | external_id | varchar(191) | NO | UNI |
wp_akd_orders | order_id | bigint(20) unsigned | NO | |
wp_akd_orders | state | varchar(32) | NO | |
wp_akd_orders | supplier_status | varchar(64) | NO | |
wp_akd_orders | updated_at | bigint(20) unsigned | NO | |
wp_allovente_myfusion_catalogue | product_id | bigint(20) unsigned | NO | PRI |
wp_allovente_myfusion_catalogue | name | text | NO | |
wp_allovente_myfusion_catalogue | sku | varchar(191) | NO | |
wp_allovente_myfusion_catalogue | ean | varchar(64) | NO | |
wp_allovente_myfusion_catalogue | category_name | varchar(191) | NO | MUL |
wp_allovente_myfusion_catalogue | brand_name | varchar(191) | NO | MUL |
wp_allovente_myfusion_catalogue | price | decimal(18,6) | YES | |
wp_allovente_myfusion_catalogue | quantity | bigint(20) | YES | |
wp_allovente_myfusion_catalogue | payload | longtext | NO | |
wp_allovente_myfusion_catalogue | selected | tinyint(4) | NO | MUL |
wp_allovente_myfusion_catalogue | target_category | bigint(20) unsigned | NO | |
wp_allovente_myfusion_catalogue | wc_id | bigint(20) unsigned | NO | |
wp_allovente_myfusion_catalogue | import_state | varchar(20) | NO | |
wp_allovente_myfusion_catalogue | import_error | text | YES | |
wp_allovente_myfusion_catalogue | details | longtext | YES | |
wp_allovente_myfusion_catalogue | import_settings | longtext | YES | |
wp_allovente_myfusion_catalogue | seen_at | datetime | NO | |
wp_allovente_sales_funnel | event_day | date | NO | PRI |
wp_allovente_sales_funnel | event_name | varchar(32) | NO | PRI |
wp_allovente_sales_funnel | device | varchar(10) | NO | PRI |
wp_allovente_sales_funnel | total | bigint(20) unsigned | NO | |
wp_cmplz_cookiebanners | ID | int(11) | NO | PRI | auto_increment
wp_cmplz_cookiebanners | title | text | NO | |
wp_cmplz_cookiebanners | banner_version | int(11) | NO | |
wp_cmplz_cookiebanners | default | int(11) | NO | |
wp_cmplz_cookiebanners | position | text | NO | |
wp_cmplz_cookiebanners | checkbox_style | text | NO | |
wp_cmplz_cookiebanners | use_logo | int(11) | NO | |
wp_cmplz_cookiebanners | logo_attachment_id | text | NO | |
wp_cmplz_cookiebanners | close_button | text | NO | |
wp_cmplz_cookiebanners | revoke | text | NO | |
wp_cmplz_cookiebanners | manage_consent_options | text | NO | |
wp_cmplz_cookiebanners | header | text | NO | |
wp_cmplz_cookiebanners | dismiss | text | NO | |
wp_cmplz_cookiebanners | save_preferences | text | NO | |
wp_cmplz_cookiebanners | view_preferences | text | NO | |
wp_cmplz_cookiebanners | category_functional | text | NO | |
wp_cmplz_cookiebanners | category_all | text | NO | |
wp_cmplz_cookiebanners | category_stats | text | NO | |
wp_cmplz_cookiebanners | category_prefs | text | NO | |
wp_cmplz_cookiebanners | accept | text | NO | |
wp_cmplz_cookiebanners | message_optin | text | NO | |
wp_cmplz_cookiebanners | use_categories | text | NO | |
wp_cmplz_cookiebanners | disable_cookiebanner | int(11) | NO | |
wp_cmplz_cookiebanners | banner_width | int(11) | NO | |
wp_cmplz_cookiebanners | soft_cookiewall | int(11) | NO | |
wp_cmplz_cookiebanners | dismiss_on_scroll | int(11) | NO | |
wp_cmplz_cookiebanners | dismiss_on_timeout | int(11) | NO | |
wp_cmplz_cookiebanners | dismiss_timeout | text | NO | |
wp_cmplz_cookiebanners | accept_informational | int(11) | NO | |
wp_cmplz_cookiebanners | message_optout | text | NO | |
wp_cmplz_cookiebanners | use_custom_cookie_css | int(11) | NO | |
wp_cmplz_cookiebanners | custom_css | text | NO | |
wp_cmplz_cookiebanners | statistics | text | NO | |
wp_cmplz_cookiebanners | functional_text | text | NO | |
wp_cmplz_cookiebanners | statistics_text | text | NO | |
wp_cmplz_cookiebanners | statistics_text_anonymous | text | NO | |
wp_cmplz_cookiebanners | preferences_text | text | NO | |
wp_cmplz_cookiebanners | marketing_text | text | NO | |
wp_cmplz_cookiebanners | colorpalette_background | text | NO | |
wp_cmplz_cookiebanners | colorpalette_text | text | NO | |
wp_cmplz_cookiebanners | colorpalette_toggles | text | NO | |
wp_cmplz_cookiebanners | colorpalette_border_radius | text | NO | |
wp_cmplz_cookiebanners | border_width | text | NO | |
wp_cmplz_cookiebanners | font_size | text | NO | |
wp_cmplz_cookiebanners | colorpalette_button_accept | text | NO | |
wp_cmplz_cookiebanners | colorpalette_button_deny | text | NO | |
wp_cmplz_cookiebanners | colorpalette_button_settings | text | NO | |
wp_cmplz_cookiebanners | buttons_border_radius | text | NO | |
wp_cmplz_cookiebanners | animation | text | NO | |
wp_cmplz_cookiebanners | use_box_shadow | int(11) | NO | |
wp_cmplz_cookiebanners | header_footer_shadow | int(11) | NO | |
wp_cmplz_cookiebanners | hide_preview | int(11) | NO | |
wp_cmplz_cookiebanners | disable_width_correction | int(11) | NO | |
wp_cmplz_cookiebanners | legal_documents | int(11) | NO | |
wp_cmplz_cookies | ID | int(11) | NO | PRI | auto_increment
wp_cmplz_cookies | name | varchar(250) | NO | |
wp_cmplz_cookies | slug | varchar(250) | NO | |
wp_cmplz_cookies | sync | int(11) | NO | |
wp_cmplz_cookies | ignored | int(11) | NO | |
wp_cmplz_cookies | retention | text | NO | |
wp_cmplz_cookies | type | text | NO | |
wp_cmplz_cookies | serviceID | int(11) | NO | |
wp_cmplz_cookies | cookieFunction | text | NO | |
wp_cmplz_cookies | collectedPersonalData | text | NO | |
wp_cmplz_cookies | purpose | text | NO | |
wp_cmplz_cookies | language | varchar(6) | NO | |
wp_cmplz_cookies | isTranslationFrom | int(11) | NO | |
wp_cmplz_cookies | isOwnDomainCookie | int(11) | NO | |
wp_cmplz_cookies | domain | text | NO | |
wp_cmplz_cookies | deleted | int(11) | NO | |
wp_cmplz_cookies | isMembersOnly | int(11) | NO | |
wp_cmplz_cookies | showOnPolicy | int(11) | NO | |
wp_cmplz_cookies | lastUpdatedDate | text | NO | |
wp_cmplz_cookies | lastAddDate | text | NO | |
wp_cmplz_cookies | firstAddDate | text | NO | |
wp_cmplz_dnsmpd | ID | int(11) | NO | PRI | auto_increment
wp_cmplz_dnsmpd | name | varchar(255) | NO | |
wp_cmplz_dnsmpd | email | varchar(255) | NO | |
wp_cmplz_dnsmpd | region | text | NO | |
wp_cmplz_dnsmpd | global_optout | int(11) | NO | |
wp_cmplz_dnsmpd | cross_context | int(11) | NO | |
wp_cmplz_dnsmpd | limit_sensitive | int(11) | NO | |
wp_cmplz_dnsmpd | request_for_access | int(11) | NO | |
wp_cmplz_dnsmpd | right_to_be_forgotten | int(11) | NO | |
wp_cmplz_dnsmpd | right_to_data_portability | int(11) | NO | |
wp_cmplz_dnsmpd | request_date | int(11) | NO | |
wp_cmplz_dnsmpd | resolved | int(11) | NO | |
wp_cmplz_services | ID | int(11) | NO | PRI | auto_increment
wp_cmplz_services | name | varchar(250) | NO | |
wp_cmplz_services | slug | varchar(250) | NO | |
wp_cmplz_services | serviceType | varchar(20) | NO | |
wp_cmplz_services | category | text | NO | |
wp_cmplz_services | thirdParty | int(11) | NO | |
wp_cmplz_services | sharesData | int(11) | NO | |
wp_cmplz_services | secondParty | int(11) | NO | |
wp_cmplz_services | privacyStatementURL | varchar(250) | NO | |
wp_cmplz_services | language | varchar(6) | NO | |
wp_cmplz_services | isTranslationFrom | int(11) | NO | |
wp_cmplz_services | sync | int(11) | NO | |
wp_cmplz_services | lastUpdatedDate | text | NO | |
wp_commentmeta | meta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_commentmeta | comment_id | bigint(20) unsigned | NO | MUL |
wp_commentmeta | meta_key | varchar(255) | YES | MUL |
wp_commentmeta | meta_value | longtext | YES | |
wp_comments | comment_ID | bigint(20) unsigned | NO | PRI | auto_increment
wp_comments | comment_post_ID | bigint(20) unsigned | NO | MUL |
wp_comments | comment_author | tinytext | NO | |
wp_comments | comment_author_email | varchar(100) | NO | MUL |
wp_comments | comment_author_url | varchar(200) | NO | |
wp_comments | comment_author_IP | varchar(100) | NO | |
wp_comments | comment_date | datetime | NO | |
wp_comments | comment_date_gmt | datetime | NO | MUL |
wp_comments | comment_content | text | NO | |
wp_comments | comment_karma | int(11) | NO | |
wp_comments | comment_approved | varchar(20) | NO | MUL |
wp_comments | comment_agent | varchar(255) | NO | |
wp_comments | comment_type | varchar(20) | NO | MUL |
wp_comments | comment_parent | bigint(20) unsigned | NO | MUL |
wp_comments | user_id | bigint(20) unsigned | NO | |
wp_e_events | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_e_events | event_data | text | YES | |
wp_e_events | created_at | datetime | NO | MUL |
wp_frmt_form_entry | entry_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_frmt_form_entry | entry_type | varchar(191) | NO | MUL |
wp_frmt_form_entry | draft_id | varchar(12) | YES | |
wp_frmt_form_entry | form_id | bigint(20) unsigned | NO | MUL |
wp_frmt_form_entry | custom_id | bigint(20) unsigned | NO | MUL |
wp_frmt_form_entry | custom_prefix | varchar(191) | NO | |
wp_frmt_form_entry | is_spam | tinyint(1) | NO | MUL |
wp_frmt_form_entry | date_created | datetime | NO | |
wp_frmt_form_entry | status | enum('active','spam','draft','abandoned','pending','failed') | NO | MUL |
wp_frmt_form_entry | date_updated | datetime | NO | |
wp_frmt_form_entry_meta | meta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_frmt_form_entry_meta | entry_id | bigint(20) unsigned | NO | MUL |
wp_frmt_form_entry_meta | meta_key | varchar(191) | YES | MUL |
wp_frmt_form_entry_meta | meta_value | longtext | YES | |
wp_frmt_form_entry_meta | date_created | datetime | NO | |
wp_frmt_form_entry_meta | date_updated | datetime | NO | |
wp_frmt_form_reports | report_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_frmt_form_reports | report_value | longtext | NO | |
wp_frmt_form_reports | status | varchar(200) | NO | |
wp_frmt_form_reports | date_created | datetime | NO | |
wp_frmt_form_reports | date_updated | datetime | NO | |
wp_frmt_form_views | view_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_frmt_form_views | form_id | bigint(20) unsigned | NO | MUL |
wp_frmt_form_views | page_id | bigint(20) unsigned | NO | |
wp_frmt_form_views | ip | varchar(191) | YES | MUL |
wp_frmt_form_views | count | mediumint(8) unsigned | NO | |
wp_frmt_form_views | date_created | datetime | NO | |
wp_frmt_form_views | date_updated | datetime | NO | |
wp_fsmpt_email_logs | id | int(10) unsigned | NO | PRI | auto_increment
wp_fsmpt_email_logs | site_id | int(11) | YES | |
wp_fsmpt_email_logs | to | text | YES | |
wp_fsmpt_email_logs | from | varchar(255) | YES | |
wp_fsmpt_email_logs | subject | varchar(255) | YES | |
wp_fsmpt_email_logs | body | longtext | YES | |
wp_fsmpt_email_logs | headers | longtext | YES | |
wp_fsmpt_email_logs | attachments | longtext | YES | |
wp_fsmpt_email_logs | status | varchar(20) | YES | |
wp_fsmpt_email_logs | response | text | YES | |
wp_fsmpt_email_logs | extra | text | YES | |
wp_fsmpt_email_logs | retries | int(10) unsigned | YES | |
wp_fsmpt_email_logs | resent_count | int(10) unsigned | YES | |
wp_fsmpt_email_logs | source | varchar(255) | YES | |
wp_fsmpt_email_logs | created_at | timestamp | YES | MUL |
wp_fsmpt_email_logs | updated_at | timestamp | YES | |
wp_gla_attribute_mapping_rules | id | bigint(20) | NO | PRI | auto_increment
wp_gla_attribute_mapping_rules | attribute | varchar(255) | NO | |
wp_gla_attribute_mapping_rules | source | varchar(100) | NO | |
wp_gla_attribute_mapping_rules | category_condition_type | varchar(10) | NO | |
wp_gla_attribute_mapping_rules | categories | text | NO | |
wp_gla_budget_recommendations | id | bigint(20) | NO | PRI | auto_increment
wp_gla_budget_recommendations | currency | varchar(3) | NO | |
wp_gla_budget_recommendations | country | varchar(2) | NO | MUL |
wp_gla_budget_recommendations | daily_budget | int(11) | NO | |
wp_gla_merchant_issues | id | bigint(20) | NO | PRI | auto_increment
wp_gla_merchant_issues | product_id | bigint(20) | NO | |
wp_gla_merchant_issues | issue | varchar(200) | NO | |
wp_gla_merchant_issues | code | varchar(100) | NO | |
wp_gla_merchant_issues | severity | varchar(20) | NO | |
wp_gla_merchant_issues | product | varchar(100) | NO | |
wp_gla_merchant_issues | action | text | NO | |
wp_gla_merchant_issues | action_url | varchar(1024) | NO | |
wp_gla_merchant_issues | applicable_countries | text | NO | |
wp_gla_merchant_issues | source | varchar(10) | NO | |
wp_gla_merchant_issues | type | varchar(10) | NO | |
wp_gla_merchant_issues | created_at | datetime | NO | |
wp_gla_merchant_price_benchmarks | product_id | bigint(20) | NO | PRI |
wp_gla_merchant_price_benchmarks | mc_product_id | varchar(255) | NO | UNI |
wp_gla_merchant_price_benchmarks | mc_product_offer_id | varchar(255) | NO | |
wp_gla_merchant_price_benchmarks | mc_product_price_micros | varchar(64) | NO | |
wp_gla_merchant_price_benchmarks | mc_product_currency_code | varchar(3) | NO | |
wp_gla_merchant_price_benchmarks | mc_price_country_code | varchar(2) | NO | |
wp_gla_merchant_price_benchmarks | mc_price_benchmark_price_micros | varchar(64) | NO | |
wp_gla_merchant_price_benchmarks | mc_price_benchmark_price_currency_code | varchar(3) | NO | |
wp_gla_merchant_price_benchmarks | mc_insights_suggested_price_micros | varchar(64) | NO | |
wp_gla_merchant_price_benchmarks | mc_insights_suggested_price_currency_code | varchar(3) | NO | |
wp_gla_merchant_price_benchmarks | mc_insights_predicted_impressions_change_fraction | decimal(10,6) | NO | |
wp_gla_merchant_price_benchmarks | mc_insights_predicted_clicks_change_fraction | decimal(10,6) | NO | |
wp_gla_merchant_price_benchmarks | mc_insights_predicted_conversions_change_fraction | decimal(10,6) | NO | |
wp_gla_merchant_price_benchmarks | mc_insights_effectiveness | tinyint(1) | NO | MUL |
wp_gla_merchant_price_benchmarks | mc_metrics_clicks | varchar(64) | NO | |
wp_gla_merchant_price_benchmarks | mc_metrics_impressions | varchar(64) | NO | |
wp_gla_merchant_price_benchmarks | mc_metrics_ctr | int(20) | NO | |
wp_gla_merchant_price_benchmarks | mc_metrics_conversions | int(20) | NO | |
wp_gla_merchant_price_benchmarks | price_compared_with_benchmark | tinyint(1) | NO | MUL |
wp_gla_shipping_rates | id | bigint(20) | NO | PRI | auto_increment
wp_gla_shipping_rates | country | varchar(2) | NO | MUL |
wp_gla_shipping_rates | currency | varchar(3) | NO | MUL |
wp_gla_shipping_rates | rate | double | NO | |
wp_gla_shipping_rates | options | text | YES | |
wp_gla_shipping_times | id | bigint(20) | NO | PRI | auto_increment
wp_gla_shipping_times | country | varchar(2) | NO | MUL |
wp_gla_shipping_times | time | bigint(20) | NO | |
wp_gla_shipping_times | max_time | bigint(20) | NO | |
wp_independent_analytics_campaigns | campaign_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_campaigns | utm_term | varchar(2048) | YES | |
wp_independent_analytics_campaigns | utm_content | varchar(2048) | YES | |
wp_independent_analytics_campaigns | landing_page_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_campaigns | utm_source_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_campaigns | utm_medium_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_campaigns | utm_campaign_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_campaign_urls | campaign_url_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_campaign_urls | path | varchar(2048) | YES | |
wp_independent_analytics_campaign_urls | utm_source | varchar(2048) | NO | |
wp_independent_analytics_campaign_urls | utm_medium | varchar(2048) | NO | |
wp_independent_analytics_campaign_urls | utm_campaign | varchar(2048) | NO | |
wp_independent_analytics_campaign_urls | utm_term | varchar(2048) | YES | |
wp_independent_analytics_campaign_urls | utm_content | varchar(2048) | YES | |
wp_independent_analytics_campaign_urls | note | varchar(2048) | YES | |
wp_independent_analytics_campaign_urls | created_at | datetime | NO | |
wp_independent_analytics_cities | city_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_cities | country_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_cities | subdivision | varchar(64) | YES | |
wp_independent_analytics_cities | city | varchar(64) | NO | |
wp_independent_analytics_clicked_links | click_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_clicked_links | link_id | bigint(20) unsigned | NO | PRI |
wp_independent_analytics_clicks | click_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_clicks | view_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_clicks | created_at | datetime | NO | |
wp_independent_analytics_click_targets | click_target_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_click_targets | target | varchar(2083) | YES | |
wp_independent_analytics_click_targets | protocol | enum('mailto','tel','sms') | YES | |
wp_independent_analytics_countries | country_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_countries | country_code | varchar(4) | NO | MUL |
wp_independent_analytics_countries | country | varchar(64) | NO | |
wp_independent_analytics_countries | continent | varchar(16) | NO | |
wp_independent_analytics_device_browsers | device_browser_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_device_browsers | device_browser | varchar(64) | NO | UNI |
wp_independent_analytics_device_oss | device_os_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_device_oss | device_os | varchar(64) | NO | UNI |
wp_independent_analytics_device_types | device_type_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_device_types | device_type | varchar(64) | NO | UNI |
wp_independent_analytics_forms | form_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_forms | plugin_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_forms | plugin_form_id | bigint(20) unsigned | NO | |
wp_independent_analytics_forms | cached_form_title | varchar(64) | NO | |
wp_independent_analytics_form_submissions | form_submission_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_form_submissions | form_id | bigint(20) unsigned | NO | |
wp_independent_analytics_form_submissions | session_id | bigint(20) unsigned | NO | |
wp_independent_analytics_form_submissions | view_id | bigint(20) unsigned | NO | |
wp_independent_analytics_form_submissions | initial_view_id | bigint(20) unsigned | NO | |
wp_independent_analytics_form_submissions | created_at | datetime | NO | |
wp_independent_analytics_landing_pages | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_landing_pages | title | varchar(512) | NO | |
wp_independent_analytics_links | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_links | link_rule_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_links | click_target_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_link_rules | link_rule_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_link_rules | name | varchar(255) | NO | |
wp_independent_analytics_link_rules | type | varchar(255) | NO | |
wp_independent_analytics_link_rules | value | varchar(255) | NO | |
wp_independent_analytics_link_rules | is_active | tinyint(1) | NO | |
wp_independent_analytics_link_rules | position | int(10) unsigned | YES | |
wp_independent_analytics_link_rules | created_at | datetime | NO | |
wp_independent_analytics_orders | order_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_orders | is_included_in_analytics | tinyint(1) | NO | |
wp_independent_analytics_orders | woocommerce_order_id | bigint(20) unsigned | YES | UNI |
wp_independent_analytics_orders | woocommerce_order_status | varchar(64) | YES | |
wp_independent_analytics_orders | surecart_order_id | varchar(36) | YES | UNI |
wp_independent_analytics_orders | surecart_order_status | varchar(64) | YES | |
wp_independent_analytics_orders | edd_order_id | bigint(20) unsigned | YES | UNI |
wp_independent_analytics_orders | edd_order_status | varchar(64) | YES | |
wp_independent_analytics_orders | pmpro_order_id | bigint(20) unsigned | YES | UNI |
wp_independent_analytics_orders | pmpro_order_status | varchar(64) | YES | |
wp_independent_analytics_orders | fluent_cart_order_id | bigint(20) unsigned | YES | UNI |
wp_independent_analytics_orders | fluent_cart_order_status | varchar(64) | YES | |
wp_independent_analytics_orders | view_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_orders | initial_view_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_orders | total | int(11) | NO | |
wp_independent_analytics_orders | total_refunded | int(11) | NO | |
wp_independent_analytics_orders | total_refunds | smallint(6) | NO | |
wp_independent_analytics_orders | is_discounted | tinyint(1) | NO | |
wp_independent_analytics_orders | created_at | datetime | NO | MUL |
wp_independent_analytics_referrers | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_referrers | domain | varchar(128) | NO | UNI |
wp_independent_analytics_referrers | referrer | varchar(128) | YES | |
wp_independent_analytics_referrers | referrer_type_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_referrer_types | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_referrer_types | referrer_type | enum('Ad','Direct','Referrer','Search','Social','AI') | NO | UNI |
wp_independent_analytics_reports | report_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_reports | user_created_report | tinyint(1) | NO | |
wp_independent_analytics_reports | name | varchar(255) | NO | |
wp_independent_analytics_reports | type | varchar(64) | NO | |
wp_independent_analytics_reports | exact_start | datetime | YES | |
wp_independent_analytics_reports | exact_end | datetime | YES | |
wp_independent_analytics_reports | relative_range_id | varchar(64) | YES | |
wp_independent_analytics_reports | sort_column | varchar(64) | YES | |
wp_independent_analytics_reports | sort_direction | varchar(64) | YES | |
wp_independent_analytics_reports | group_name | varchar(64) | YES | |
wp_independent_analytics_reports | quick_stats | text | YES | |
wp_independent_analytics_reports | chart_interval | varchar(64) | YES | |
wp_independent_analytics_reports | columns | text | YES | |
wp_independent_analytics_reports | filter_logic | enum('and','or') | NO | |
wp_independent_analytics_reports | filters | text | YES | |
wp_independent_analytics_reports | position | int(11) | YES | |
wp_independent_analytics_reports | primary_chart_metric_id | varchar(255) | YES | |
wp_independent_analytics_reports | secondary_chart_metric_id | varchar(255) | YES | |
wp_independent_analytics_resources | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_resources | resource | varchar(256) | NO | |
wp_independent_analytics_resources | singular_id | bigint(20) unsigned | YES | |
wp_independent_analytics_resources | author_id | bigint(20) unsigned | YES | |
wp_independent_analytics_resources | virtual_page_id | varchar(64) | YES | |
wp_independent_analytics_resources | date_archive | varchar(256) | YES | |
wp_independent_analytics_resources | search_query | varchar(256) | YES | |
wp_independent_analytics_resources | post_type | varchar(256) | YES | |
wp_independent_analytics_resources | term_id | bigint(20) unsigned | YES | |
wp_independent_analytics_resources | not_found_url | varchar(2083) | YES | |
wp_independent_analytics_resources | cached_title | varchar(256) | YES | |
wp_independent_analytics_resources | cached_url | varchar(2083) | YES | |
wp_independent_analytics_resources | cached_type | varchar(256) | YES | |
wp_independent_analytics_resources | cached_type_label | varchar(256) | YES | |
wp_independent_analytics_resources | cached_author_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_resources | cached_author | varchar(256) | YES | |
wp_independent_analytics_resources | cached_category | varchar(256) | YES | |
wp_independent_analytics_resources | cached_date | date | YES | |
wp_independent_analytics_sessions | session_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_sessions | old_visitor_id | varchar(32) | YES | MUL |
wp_independent_analytics_sessions | visitor_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | initial_view_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | referrer_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | campaign_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | created_at | datetime | NO | MUL |
wp_independent_analytics_sessions | legacy_view | tinyint(1) | NO | |
wp_independent_analytics_sessions | final_view_id | bigint(20) unsigned | YES | |
wp_independent_analytics_sessions | ended_at | datetime | YES | |
wp_independent_analytics_sessions | city_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | country_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | total_views | int(11) | YES | |
wp_independent_analytics_sessions | device_type_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | device_os_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | device_browser_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_sessions | is_first_session | tinyint(1) | YES | |
wp_independent_analytics_utm_campaigns | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_utm_campaigns | utm_campaign | varchar(512) | NO | |
wp_independent_analytics_utm_mediums | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_utm_mediums | utm_medium | varchar(512) | NO | |
wp_independent_analytics_utm_sources | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_utm_sources | utm_source | varchar(512) | NO | |
wp_independent_analytics_views | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_views | resource_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_views | viewed_at | datetime | YES | MUL |
wp_independent_analytics_views | page | bigint(20) unsigned | NO | |
wp_independent_analytics_views | session_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_views | next_view_id | bigint(20) unsigned | YES | |
wp_independent_analytics_views | next_viewed_at | datetime | YES | |
wp_independent_analytics_visitors | visitor_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_independent_analytics_visitors | hash | varchar(32) | NO | UNI |
wp_independent_analytics_wc_orders | order_id | bigint(20) unsigned | NO | PRI |
wp_independent_analytics_wc_orders | view_id | bigint(20) unsigned | NO | MUL |
wp_independent_analytics_wc_orders | initial_view_id | bigint(20) unsigned | YES | MUL |
wp_independent_analytics_wc_orders | created_at | datetime | NO | MUL |
wp_independent_analytics_wc_orders | total | double | YES | |
wp_independent_analytics_wc_orders | total_refunded | double | YES | |
wp_independent_analytics_wc_orders | total_refunds | smallint(6) | YES | |
wp_independent_analytics_wc_orders | status | varchar(200) | YES | |
wp_keybin_logs | id | bigint(20) | NO | PRI | auto_increment
wp_keybin_logs | log_type | varchar(50) | NO | |
wp_keybin_logs | status | varchar(20) | NO | |
wp_keybin_logs | message | text | YES | |
wp_keybin_logs | details | longtext | YES | |
wp_keybin_logs | created_at | timestamp | YES | |
wp_links | link_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_links | link_url | varchar(255) | NO | |
wp_links | link_name | varchar(255) | NO | |
wp_links | link_image | varchar(255) | NO | |
wp_links | link_target | varchar(25) | NO | |
wp_links | link_description | varchar(255) | NO | |
wp_links | link_visible | varchar(20) | NO | MUL |
wp_links | link_owner | bigint(20) unsigned | NO | |
wp_links | link_rating | int(11) | NO | |
wp_links | link_updated | datetime | NO | |
wp_links | link_rel | varchar(255) | NO | |
wp_links | link_notes | mediumtext | NO | |
wp_links | link_rss | varchar(255) | NO | |
wp_mwai_filemeta | meta_id | bigint(20) | NO | PRI | auto_increment
wp_mwai_filemeta | file_id | bigint(20) | NO | |
wp_mwai_filemeta | meta_key | varchar(255) | YES | |
wp_mwai_filemeta | meta_value | longtext | YES | |
wp_mwai_files | id | bigint(20) | NO | PRI | auto_increment
wp_mwai_files | refId | varchar(64) | NO | UNI |
wp_mwai_files | envId | varchar(128) | YES | |
wp_mwai_files | userId | varchar(64) | YES | |
wp_mwai_files | type | varchar(32) | YES | |
wp_mwai_files | status | varchar(32) | YES | |
wp_mwai_files | purpose | varchar(32) | YES | |
wp_mwai_files | created | datetime | NO | |
wp_mwai_files | updated | datetime | NO | |
wp_mwai_files | expires | datetime | YES | |
wp_mwai_files | path | text | YES | |
wp_mwai_files | url | text | YES | |
wp_mwai_tasklogs | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_mwai_tasklogs | task_id | bigint(20) unsigned | NO | MUL |
wp_mwai_tasklogs | started | datetime | NO | |
wp_mwai_tasklogs | ended | datetime | YES | |
wp_mwai_tasklogs | status | varchar(16) | NO | |
wp_mwai_tasklogs | message | text | YES | |
wp_mwai_tasklogs | time_taken | float | YES | |
wp_mwai_tasklogs | memory_peak | bigint(20) | YES | |
wp_mwai_tasklogs | step | int(11) | YES | |
wp_mwai_tasklogs | created | datetime | NO | |
wp_mwai_tasks | id | bigint(20) | NO | PRI | auto_increment
wp_mwai_tasks | task_name | varchar(100) | NO | UNI |
wp_mwai_tasks | description | text | YES | |
wp_mwai_tasks | category | varchar(32) | NO | MUL |
wp_mwai_tasks | schedule | varchar(128) | NO | |
wp_mwai_tasks | status | varchar(16) | NO | MUL |
wp_mwai_tasks | next_run | datetime | YES | |
wp_mwai_tasks | last_run | datetime | YES | |
wp_mwai_tasks | expires_at | datetime | YES | MUL |
wp_mwai_tasks | step | int(11) | NO | |
wp_mwai_tasks | step_name | varchar(64) | YES | |
wp_mwai_tasks | step_data | longtext | YES | |
wp_mwai_tasks | data | longtext | YES | |
wp_mwai_tasks | meta | longtext | YES | |
wp_mwai_tasks | error_count | int(11) | NO | |
wp_mwai_tasks | max_retries | int(11) | NO | |
wp_mwai_tasks | created | datetime | NO | |
wp_mwai_tasks | updated | datetime | NO | |
wp_options | option_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_options | option_name | varchar(191) | NO | UNI |
wp_options | option_value | longtext | NO | |
wp_options | autoload | varchar(20) | NO | MUL |
wp_packlink_entity | id | int(11) | NO | PRI | auto_increment
wp_packlink_entity | type | varchar(127) | YES | |
wp_packlink_entity | index_1 | varchar(127) | YES | |
wp_packlink_entity | index_2 | varchar(127) | YES | |
wp_packlink_entity | index_3 | varchar(127) | YES | |
wp_packlink_entity | index_4 | varchar(127) | YES | |
wp_packlink_entity | index_5 | varchar(127) | YES | |
wp_packlink_entity | index_6 | varchar(127) | YES | |
wp_packlink_entity | index_7 | varchar(127) | YES | |
wp_packlink_entity | index_8 | varchar(127) | YES | |
wp_packlink_entity | data | longtext | YES | |
wp_pmxi_files | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_pmxi_files | import_id | bigint(20) unsigned | NO | |
wp_pmxi_files | name | text | YES | |
wp_pmxi_files | path | text | YES | |
wp_pmxi_files | registered_on | datetime | NO | |
wp_pmxi_hash | hash | binary(16) | NO | PRI |
wp_pmxi_hash | post_id | bigint(20) | NO | |
wp_pmxi_hash | import_id | smallint(5) unsigned | NO | |
wp_pmxi_hash | post_type | varchar(32) | NO | |
wp_pmxi_history | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_pmxi_history | import_id | bigint(20) unsigned | NO | |
wp_pmxi_history | type | enum('manual','processing','trigger','continue','cli','') | NO | |
wp_pmxi_history | time_run | text | NO | |
wp_pmxi_history | date | datetime | NO | |
wp_pmxi_history | summary | text | NO | |
wp_pmxi_images | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_pmxi_images | attachment_id | bigint(20) unsigned | NO | |
wp_pmxi_images | image_url | text | YES | |
wp_pmxi_images | image_filename | text | YES | |
wp_pmxi_imports | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_pmxi_imports | parent_import_id | bigint(20) | NO | |
wp_pmxi_imports | name | text | YES | |
wp_pmxi_imports | friendly_name | varchar(255) | NO | |
wp_pmxi_imports | type | varchar(32) | YES | |
wp_pmxi_imports | feed_type | enum('xml','csv','zip','gz','') | NO | |
wp_pmxi_imports | path | text | YES | |
wp_pmxi_imports | xpath | text | YES | |
wp_pmxi_imports | options | longtext | YES | |
wp_pmxi_imports | registered_on | datetime | NO | |
wp_pmxi_imports | root_element | varchar(255) | YES | |
wp_pmxi_imports | processing | tinyint(1) | NO | |
wp_pmxi_imports | executing | tinyint(1) | NO | |
wp_pmxi_imports | triggered | tinyint(1) | NO | |
wp_pmxi_imports | queue_chunk_number | bigint(20) | NO | |
wp_pmxi_imports | first_import | timestamp | NO | |
wp_pmxi_imports | count | bigint(20) | NO | |
wp_pmxi_imports | imported | bigint(20) | NO | |
wp_pmxi_imports | created | bigint(20) | NO | |
wp_pmxi_imports | updated | bigint(20) | NO | |
wp_pmxi_imports | skipped | bigint(20) | NO | |
wp_pmxi_imports | deleted | bigint(20) | NO | |
wp_pmxi_imports | changed_missing | bigint(20) | NO | |
wp_pmxi_imports | canceled | tinyint(1) | NO | |
wp_pmxi_imports | canceled_on | datetime | NO | |
wp_pmxi_imports | failed | tinyint(1) | NO | |
wp_pmxi_imports | failed_on | datetime | NO | |
wp_pmxi_imports | settings_update_on | datetime | NO | |
wp_pmxi_imports | last_activity | datetime | NO | |
wp_pmxi_imports | iteration | bigint(20) | NO | |
wp_pmxi_posts | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_pmxi_posts | post_id | bigint(20) | NO | |
wp_pmxi_posts | import_id | bigint(20) unsigned | NO | |
wp_pmxi_posts | unique_key | text | YES | |
wp_pmxi_posts | product_key | text | YES | |
wp_pmxi_posts | iteration | bigint(20) | NO | |
wp_pmxi_posts | specified | tinyint(1) | NO | |
wp_pmxi_templates | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_pmxi_templates | options | longtext | YES | |
wp_pmxi_templates | scheduled | varchar(64) | NO | |
wp_pmxi_templates | name | varchar(200) | NO | |
wp_pmxi_templates | title | text | YES | |
wp_pmxi_templates | content | longtext | YES | |
wp_pmxi_templates | is_keep_linebreaks | tinyint(1) | NO | |
wp_pmxi_templates | is_leave_html | tinyint(1) | NO | |
wp_pmxi_templates | fix_characters | tinyint(1) | NO | |
wp_pmxi_templates | meta | longtext | YES | |
wp_postmeta | meta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_postmeta | post_id | bigint(20) unsigned | NO | MUL |
wp_postmeta | meta_key | varchar(255) | YES | MUL |
wp_postmeta | meta_value | longtext | YES | |
wp_posts | ID | bigint(20) unsigned | NO | PRI | auto_increment
wp_posts | post_author | bigint(20) unsigned | NO | MUL |
wp_posts | post_date | datetime | NO | |
wp_posts | post_date_gmt | datetime | NO | |
wp_posts | post_content | longtext | NO | |
wp_posts | post_title | text | NO | |
wp_posts | post_excerpt | text | NO | |
wp_posts | post_status | varchar(20) | NO | |
wp_posts | comment_status | varchar(20) | NO | |
wp_posts | ping_status | varchar(20) | NO | |
wp_posts | post_password | varchar(255) | NO | |
wp_posts | post_name | varchar(200) | NO | MUL |
wp_posts | to_ping | text | NO | |
wp_posts | pinged | text | NO | |
wp_posts | post_modified | datetime | NO | |
wp_posts | post_modified_gmt | datetime | NO | |
wp_posts | post_content_filtered | longtext | NO | |
wp_posts | post_parent | bigint(20) unsigned | NO | MUL |
wp_posts | guid | varchar(255) | NO | |
wp_posts | menu_order | int(11) | NO | |
wp_posts | post_type | varchar(20) | NO | MUL |
wp_posts | post_mime_type | varchar(100) | NO | |
wp_posts | comment_count | bigint(20) | NO | |
wp_rank_math_analytics_gsc | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_rank_math_analytics_gsc | created | timestamp | NO | |
wp_rank_math_analytics_gsc | query | varchar(1000) | NO | MUL |
wp_rank_math_analytics_gsc | page | varchar(500) | NO | MUL |
wp_rank_math_analytics_gsc | clicks | mediumint(6) | NO | MUL |
wp_rank_math_analytics_gsc | impressions | mediumint(6) | NO | |
wp_rank_math_analytics_gsc | position | double | NO | MUL |
wp_rank_math_analytics_gsc | ctr | double | NO | |
wp_rank_math_analytics_inspections | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_rank_math_analytics_inspections | page | varchar(500) | NO | MUL |
wp_rank_math_analytics_inspections | created | timestamp | NO | MUL |
wp_rank_math_analytics_inspections | index_verdict | varchar(64) | NO | MUL |
wp_rank_math_analytics_inspections | indexing_state | varchar(64) | NO | |
wp_rank_math_analytics_inspections | coverage_state | text | NO | |
wp_rank_math_analytics_inspections | page_fetch_state | varchar(64) | NO | MUL |
wp_rank_math_analytics_inspections | robots_txt_state | varchar(64) | NO | MUL |
wp_rank_math_analytics_inspections | rich_results_verdict | varchar(64) | NO | MUL |
wp_rank_math_analytics_inspections | rich_results_items | longtext | NO | |
wp_rank_math_analytics_inspections | last_crawl_time | timestamp | NO | |
wp_rank_math_analytics_inspections | crawled_as | varchar(64) | NO | |
wp_rank_math_analytics_inspections | google_canonical | text | NO | |
wp_rank_math_analytics_inspections | user_canonical | text | NO | |
wp_rank_math_analytics_inspections | sitemap | text | NO | |
wp_rank_math_analytics_inspections | referring_urls | longtext | NO | |
wp_rank_math_analytics_inspections | raw_api_response | longtext | NO | |
wp_rank_math_analytics_objects | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_rank_math_analytics_objects | created | timestamp | NO | |
wp_rank_math_analytics_objects | title | text | NO | |
wp_rank_math_analytics_objects | page | varchar(500) | NO | MUL |
wp_rank_math_analytics_objects | object_type | varchar(100) | NO | |
wp_rank_math_analytics_objects | object_subtype | varchar(100) | NO | |
wp_rank_math_analytics_objects | object_id | bigint(20) | NO | |
wp_rank_math_analytics_objects | primary_key | varchar(255) | NO | |
wp_rank_math_analytics_objects | seo_score | tinyint(4) | NO | |
wp_rank_math_analytics_objects | page_score | tinyint(4) | NO | |
wp_rank_math_analytics_objects | is_indexable | tinyint(1) | NO | |
wp_rank_math_analytics_objects | schemas_in_use | varchar(500) | YES | |
wp_rank_math_analytics_objects | desktop_interactive | double | YES | |
wp_rank_math_analytics_objects | desktop_pagescore | double | YES | |
wp_rank_math_analytics_objects | mobile_interactive | double | YES | |
wp_rank_math_analytics_objects | mobile_pagescore | double | YES | |
wp_rank_math_analytics_objects | pagespeed_refreshed | timestamp | YES | |
wp_rank_math_internal_links | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_rank_math_internal_links | url | varchar(255) | NO | |
wp_rank_math_internal_links | post_id | bigint(20) unsigned | NO | MUL |
wp_rank_math_internal_links | target_post_id | bigint(20) unsigned | NO | MUL |
wp_rank_math_internal_links | type | varchar(8) | NO | |
wp_rank_math_internal_meta | object_id | bigint(20) unsigned | NO | PRI |
wp_rank_math_internal_meta | internal_link_count | int(10) unsigned | YES | |
wp_rank_math_internal_meta | external_link_count | int(10) unsigned | YES | |
wp_rank_math_internal_meta | incoming_link_count | int(10) unsigned | YES | |
wp_redirection_404 | id | int(10) unsigned | NO | PRI | auto_increment
wp_redirection_404 | created | datetime | NO | MUL |
wp_redirection_404 | url | mediumtext | NO | |
wp_redirection_404 | domain | varchar(255) | YES | |
wp_redirection_404 | agent | varchar(255) | YES | |
wp_redirection_404 | referrer | varchar(255) | YES | MUL |
wp_redirection_404 | http_code | int(10) unsigned | NO | |
wp_redirection_404 | request_method | varchar(10) | YES | |
wp_redirection_404 | request_data | mediumtext | YES | |
wp_redirection_404 | ip | varchar(45) | YES | MUL |
wp_redirection_groups | id | int(10) unsigned | NO | PRI | auto_increment
wp_redirection_groups | name | varchar(50) | NO | |
wp_redirection_groups | tracking | int(11) | NO | |
wp_redirection_groups | module_id | int(10) unsigned | NO | MUL |
wp_redirection_groups | status | enum('enabled','disabled') | NO | MUL |
wp_redirection_groups | position | int(10) unsigned | NO | |
wp_redirection_items | id | int(10) unsigned | NO | PRI | auto_increment
wp_redirection_items | url | mediumtext | NO | MUL |
wp_redirection_items | match_url | varchar(2000) | YES | MUL |
wp_redirection_items | match_data | text | YES | |
wp_redirection_items | regex | int(10) unsigned | NO | MUL |
wp_redirection_items | position | int(10) unsigned | NO | |
wp_redirection_items | last_count | int(10) unsigned | NO | |
wp_redirection_items | last_access | datetime | NO | |
wp_redirection_items | group_id | int(11) | NO | MUL |
wp_redirection_items | status | enum('enabled','disabled') | NO | MUL |
wp_redirection_items | action_type | varchar(20) | NO | |
wp_redirection_items | action_code | int(10) unsigned | NO | |
wp_redirection_items | action_data | mediumtext | YES | |
wp_redirection_items | match_type | varchar(20) | NO | |
wp_redirection_items | title | text | YES | |
wp_redirection_logs | id | int(10) unsigned | NO | PRI | auto_increment
wp_redirection_logs | created | datetime | NO | MUL |
wp_redirection_logs | url | mediumtext | NO | |
wp_redirection_logs | domain | varchar(255) | YES | |
wp_redirection_logs | sent_to | mediumtext | YES | |
wp_redirection_logs | agent | mediumtext | YES | |
wp_redirection_logs | referrer | mediumtext | YES | |
wp_redirection_logs | http_code | int(10) unsigned | NO | |
wp_redirection_logs | request_method | varchar(10) | YES | |
wp_redirection_logs | request_data | mediumtext | YES | |
wp_redirection_logs | redirect_by | varchar(50) | YES | |
wp_redirection_logs | redirection_id | int(10) unsigned | YES | MUL |
wp_redirection_logs | ip | varchar(45) | YES | MUL |
wp_snippets | id | bigint(20) | NO | PRI | auto_increment
wp_snippets | name | tinytext | NO | |
wp_snippets | description | text | NO | |
wp_snippets | code | longtext | NO | |
wp_snippets | tags | longtext | NO | |
wp_snippets | scope | varchar(15) | NO | MUL |
wp_snippets | condition_id | int(11) | NO | |
wp_snippets | priority | smallint(6) | NO | |
wp_snippets | active | tinyint(1) | NO | MUL |
wp_snippets | modified | datetime | NO | |
wp_snippets | revision | bigint(20) | NO | |
wp_snippets | cloud_id | bigint(20) | YES | |
wp_srfm_entries | ID | bigint(20) unsigned | NO | PRI | auto_increment
wp_srfm_entries | form_id | bigint(20) unsigned | YES | MUL |
wp_srfm_entries | user_id | bigint(20) unsigned | YES | MUL |
wp_srfm_entries | form_data | longtext | YES | |
wp_srfm_entries | logs | longtext | YES | |
wp_srfm_entries | notes | longtext | YES | |
wp_srfm_entries | submission_info | longtext | YES | |
wp_srfm_entries | status | varchar(10) | YES | |
wp_srfm_entries | type | varchar(20) | YES | |
wp_srfm_entries | extras | longtext | YES | |
wp_srfm_entries | created_at | datetime | NO | |
wp_srfm_entries | updated_at | datetime | NO | on update current_timestamp()
wp_srfm_payments | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_srfm_payments | form_id | bigint(20) unsigned | YES | MUL |
wp_srfm_payments | block_id | varchar(255) | NO | |
wp_srfm_payments | status | varchar(50) | NO | |
wp_srfm_payments | total_amount | decimal(26,8) | NO | |
wp_srfm_payments | refunded_amount | decimal(26,8) | NO | |
wp_srfm_payments | currency | varchar(10) | NO | |
wp_srfm_payments | entry_id | bigint(20) unsigned | YES | |
wp_srfm_payments | gateway | varchar(20) | NO | |
wp_srfm_payments | type | varchar(30) | NO | |
wp_srfm_payments | mode | varchar(20) | NO | |
wp_srfm_payments | transaction_id | varchar(50) | NO | |
wp_srfm_payments | customer_id | varchar(50) | NO | |
wp_srfm_payments | subscription_id | varchar(50) | YES | |
wp_srfm_payments | subscription_status | varchar(50) | YES | |
wp_srfm_payments | parent_subscription_id | bigint(20) unsigned | YES | |
wp_srfm_payments | payment_data | longtext | YES | |
wp_srfm_payments | extra | longtext | YES | |
wp_srfm_payments | log | longtext | YES | |
wp_srfm_payments | created_at | datetime | NO | |
wp_srfm_payments | updated_at | datetime | NO | on update current_timestamp()
wp_srfm_payments | srfm_txn_id | varchar(100) | NO | |
wp_srfm_payments | customer_email | varchar(255) | YES | |
wp_srfm_payments | customer_name | varchar(255) | YES | |
wp_surecart_incoming_webhooks | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_surecart_incoming_webhooks | webhook_id | varchar(155) | NO | MUL |
wp_surecart_incoming_webhooks | data | longtext | NO | |
wp_surecart_incoming_webhooks | processed_at | timestamp | YES | MUL |
wp_surecart_incoming_webhooks | source | varchar(155) | NO | |
wp_surecart_incoming_webhooks | created_at | timestamp | NO | MUL |
wp_surecart_incoming_webhooks | updated_at | timestamp | YES | |
wp_surecart_incoming_webhooks | deleted_at | timestamp | YES | |
wp_surecart_integrations | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_surecart_integrations | model_name | varchar(155) | YES | |
wp_surecart_integrations | model_id | varchar(155) | NO | MUL |
wp_surecart_integrations | price_id | varchar(155) | YES | |
wp_surecart_integrations | variant_id | varchar(155) | YES | |
wp_surecart_integrations | integration_id | varchar(155) | YES | MUL |
wp_surecart_integrations | provider | varchar(155) | NO | |
wp_surecart_integrations | created_at | timestamp | NO | MUL |
wp_surecart_integrations | updated_at | timestamp | YES | |
wp_surecart_integrations | deleted_at | timestamp | YES | |
wp_surecart_variant_option_values | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_surecart_variant_option_values | value | varchar(155) | NO | MUL |
wp_surecart_variant_option_values | name | varchar(155) | NO | MUL |
wp_surecart_variant_option_values | post_id | bigint(20) unsigned | NO | MUL |
wp_surecart_variant_option_values | product_id | varchar(155) | NO | MUL |
wp_surecart_variant_option_values | account_id | varchar(155) | NO | MUL |
wp_surecart_variant_option_values | created_at | timestamp | NO | MUL |
wp_surecart_variant_option_values | updated_at | timestamp | YES | |
wp_surecookie_consent_log | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_surecookie_consent_log | ip_address | varchar(45) | NO | MUL |
wp_surecookie_consent_log | user_id | bigint(20) unsigned | NO | MUL |
wp_surecookie_consent_log | session_id | varchar(36) | NO | MUL |
wp_surecookie_consent_log | preferences | longtext | NO | |
wp_surecookie_consent_log | action | enum('accepted','declined','partially_accepted') | NO | MUL |
wp_surecookie_consent_log | country | varchar(100) | YES | |
wp_surecookie_consent_log | geo_preset_id | varchar(100) | NO | MUL |
wp_surecookie_consent_log | is_forwarded | tinyint(1) | NO | MUL |
wp_surecookie_consent_log | origin_site | varchar(255) | YES | |
wp_surecookie_consent_log | forwarded_to | text | YES | |
wp_surecookie_consent_log | timestamp | datetime | NO | MUL |
wp_suretriggers_webhook_requests | id | mediumint(9) | NO | PRI | auto_increment
wp_suretriggers_webhook_requests | request_method | varchar(255) | YES | |
wp_suretriggers_webhook_requests | request_url | varchar(255) | NO | |
wp_suretriggers_webhook_requests | request_data | longtext | YES | |
wp_suretriggers_webhook_requests | response_code | int(11) | NO | |
wp_suretriggers_webhook_requests | status | varchar(20) | NO | |
wp_suretriggers_webhook_requests | error_info | varchar(255) | YES | |
wp_suretriggers_webhook_requests | retry_attempts | int(11) | YES | |
wp_suretriggers_webhook_requests | processed_at | datetime | YES | |
wp_suretriggers_webhook_requests | created_at | datetime | YES | |
wp_suretriggers_webhook_requests | updated_at | datetime | YES | on update current_timestamp()
wp_termmeta | meta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_termmeta | term_id | bigint(20) unsigned | NO | MUL |
wp_termmeta | meta_key | varchar(255) | YES | MUL |
wp_termmeta | meta_value | longtext | YES | |
wp_terms | term_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_terms | name | varchar(200) | NO | MUL |
wp_terms | slug | varchar(200) | NO | MUL |
wp_terms | term_group | bigint(20) | NO | |
wp_term_relationships | object_id | bigint(20) unsigned | NO | PRI |
wp_term_relationships | term_taxonomy_id | bigint(20) unsigned | NO | PRI |
wp_term_relationships | term_order | int(11) | NO | |
wp_term_taxonomy | term_taxonomy_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_term_taxonomy | term_id | bigint(20) unsigned | NO | MUL |
wp_term_taxonomy | taxonomy | varchar(32) | NO | MUL |
wp_term_taxonomy | description | longtext | NO | |
wp_term_taxonomy | parent | bigint(20) unsigned | NO | |
wp_term_taxonomy | count | bigint(20) | NO | |
wp_trp_dictionary_fr_fr_en_us | id | bigint(20) | NO | PRI | auto_increment
wp_trp_dictionary_fr_fr_en_us | original | longtext | NO | MUL |
wp_trp_dictionary_fr_fr_en_us | translated | longtext | YES | |
wp_trp_dictionary_fr_fr_en_us | status | int(11) | YES | |
wp_trp_dictionary_fr_fr_en_us | block_type | int(11) | YES | MUL |
wp_trp_dictionary_fr_fr_en_us | original_id | bigint(20) | YES | |
wp_trp_gettext_en_us | id | bigint(20) | NO | PRI | auto_increment
wp_trp_gettext_en_us | original | longtext | NO | MUL |
wp_trp_gettext_en_us | translated | longtext | YES | |
wp_trp_gettext_en_us | domain | longtext | YES | |
wp_trp_gettext_en_us | status | int(11) | YES | |
wp_trp_gettext_en_us | original_id | bigint(20) | YES | MUL |
wp_trp_gettext_en_us | plural_form | int(11) | YES | |
wp_trp_gettext_fr_fr | id | bigint(20) | NO | PRI | auto_increment
wp_trp_gettext_fr_fr | original | longtext | NO | MUL |
wp_trp_gettext_fr_fr | translated | longtext | YES | |
wp_trp_gettext_fr_fr | domain | longtext | YES | |
wp_trp_gettext_fr_fr | status | int(11) | YES | |
wp_trp_gettext_fr_fr | original_id | bigint(20) | YES | MUL |
wp_trp_gettext_fr_fr | plural_form | int(11) | YES | |
wp_trp_gettext_original_meta | meta_id | bigint(20) | NO | PRI | auto_increment
wp_trp_gettext_original_meta | original_id | bigint(20) | NO | MUL |
wp_trp_gettext_original_meta | meta_key | varchar(255) | YES | MUL |
wp_trp_gettext_original_meta | meta_value | longtext | YES | |
wp_trp_gettext_original_strings | id | bigint(20) | NO | PRI | auto_increment
wp_trp_gettext_original_strings | original | text | NO | MUL |
wp_trp_gettext_original_strings | domain | text | YES | |
wp_trp_gettext_original_strings | context | text | YES | |
wp_trp_gettext_original_strings | original_plural | text | YES | |
wp_trp_gettext_original_strings | lookup_hash | char(32) | NO | UNI |
wp_trp_original_meta | meta_id | bigint(20) | NO | PRI | auto_increment
wp_trp_original_meta | original_id | bigint(20) | NO | MUL |
wp_trp_original_meta | meta_key | varchar(255) | YES | MUL |
wp_trp_original_meta | meta_value | longtext | YES | |
wp_trp_original_strings | id | bigint(20) | NO | PRI | auto_increment
wp_trp_original_strings | original | text | NO | MUL |
wp_usermeta | umeta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_usermeta | user_id | bigint(20) unsigned | NO | MUL |
wp_usermeta | meta_key | varchar(255) | YES | MUL |
wp_usermeta | meta_value | longtext | YES | |
wp_users | ID | bigint(20) unsigned | NO | PRI | auto_increment
wp_users | user_login | varchar(60) | NO | MUL |
wp_users | user_pass | varchar(255) | NO | |
wp_users | user_nicename | varchar(50) | NO | MUL |
wp_users | user_email | varchar(100) | NO | MUL |
wp_users | user_url | varchar(100) | NO | |
wp_users | user_registered | datetime | NO | |
wp_users | user_activation_key | varchar(255) | NO | |
wp_users | user_status | int(11) | NO | |
wp_users | display_name | varchar(250) | NO | |
wp_wcpdf_invoice_number | id | int(16) | NO | PRI | auto_increment
wp_wcpdf_invoice_number | order_id | int(16) | YES | MUL |
wp_wcpdf_invoice_number | date | datetime | NO | |
wp_wcpdf_invoice_number | calculated_number | int(16) | YES | |
wp_wcpdf_packing_slip_number | id | int(16) | NO | PRI | auto_increment
wp_wcpdf_packing_slip_number | order_id | int(16) | YES | MUL |
wp_wcpdf_packing_slip_number | date | datetime | NO | |
wp_wcpdf_packing_slip_number | calculated_number | int(16) | YES | |
wp_wc_admin_notes | note_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_admin_notes | name | varchar(255) | NO | |
wp_wc_admin_notes | type | varchar(20) | NO | |
wp_wc_admin_notes | locale | varchar(20) | NO | |
wp_wc_admin_notes | title | longtext | NO | |
wp_wc_admin_notes | content | longtext | NO | |
wp_wc_admin_notes | content_data | longtext | YES | |
wp_wc_admin_notes | status | varchar(200) | NO | |
wp_wc_admin_notes | source | varchar(200) | NO | |
wp_wc_admin_notes | date_created | datetime | NO | |
wp_wc_admin_notes | date_reminder | datetime | YES | |
wp_wc_admin_notes | is_snoozable | tinyint(1) | NO | |
wp_wc_admin_notes | layout | varchar(20) | NO | |
wp_wc_admin_notes | image | varchar(200) | YES | |
wp_wc_admin_notes | is_deleted | tinyint(1) | NO | |
wp_wc_admin_notes | is_read | tinyint(1) | NO | |
wp_wc_admin_notes | icon | varchar(200) | NO | |
wp_wc_admin_note_actions | action_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_admin_note_actions | note_id | bigint(20) unsigned | NO | MUL |
wp_wc_admin_note_actions | name | varchar(255) | NO | |
wp_wc_admin_note_actions | label | varchar(255) | NO | |
wp_wc_admin_note_actions | query | longtext | NO | |
wp_wc_admin_note_actions | status | varchar(255) | NO | |
wp_wc_admin_note_actions | actioned_text | varchar(255) | NO | |
wp_wc_admin_note_actions | nonce_action | varchar(255) | YES | |
wp_wc_admin_note_actions | nonce_name | varchar(255) | YES | |
wp_wc_category_lookup | category_tree_id | bigint(20) unsigned | NO | PRI |
wp_wc_category_lookup | category_id | bigint(20) unsigned | NO | PRI |
wp_wc_customer_lookup | customer_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_customer_lookup | user_id | bigint(20) unsigned | YES | UNI |
wp_wc_customer_lookup | username | varchar(60) | NO | |
wp_wc_customer_lookup | first_name | varchar(255) | NO | |
wp_wc_customer_lookup | last_name | varchar(255) | NO | |
wp_wc_customer_lookup | email | varchar(100) | YES | MUL |
wp_wc_customer_lookup | date_last_active | timestamp | YES | |
wp_wc_customer_lookup | date_registered | timestamp | YES | |
wp_wc_customer_lookup | country | char(2) | NO | |
wp_wc_customer_lookup | postcode | varchar(20) | NO | |
wp_wc_customer_lookup | city | varchar(100) | NO | |
wp_wc_customer_lookup | state | varchar(100) | NO | |
wp_wc_customer_lookup | billing_phone | varchar(100) | NO | |
wp_wc_customer_lookup | shipping_phone | varchar(100) | NO | |
wp_wc_download_log | download_log_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_download_log | timestamp | datetime | NO | MUL |
wp_wc_download_log | permission_id | bigint(20) unsigned | NO | MUL |
wp_wc_download_log | user_id | bigint(20) unsigned | YES | |
wp_wc_download_log | user_ip_address | varchar(100) | YES | |
wp_wc_orders | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_orders | status | varchar(20) | YES | MUL |
wp_wc_orders | currency | varchar(10) | YES | |
wp_wc_orders | type | varchar(20) | YES | MUL |
wp_wc_orders | tax_amount | decimal(26,8) | YES | |
wp_wc_orders | total_amount | decimal(26,8) | YES | |
wp_wc_orders | customer_id | bigint(20) unsigned | YES | MUL |
wp_wc_orders | billing_email | varchar(320) | YES | MUL |
wp_wc_orders | date_created_gmt | datetime | YES | MUL |
wp_wc_orders | date_updated_gmt | datetime | YES | MUL |
wp_wc_orders | parent_order_id | bigint(20) unsigned | YES | MUL |
wp_wc_orders | payment_method | varchar(100) | YES | |
wp_wc_orders | payment_method_title | text | YES | |
wp_wc_orders | transaction_id | varchar(100) | YES | MUL |
wp_wc_orders | ip_address | varchar(100) | YES | |
wp_wc_orders | user_agent | text | YES | |
wp_wc_orders | customer_note | text | YES | |
wp_wc_orders_meta | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_orders_meta | order_id | bigint(20) unsigned | YES | MUL |
wp_wc_orders_meta | meta_key | varchar(255) | YES | MUL |
wp_wc_orders_meta | meta_value | text | YES | |
wp_wc_order_addresses | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_order_addresses | order_id | bigint(20) unsigned | YES | MUL |
wp_wc_order_addresses | address_type | varchar(20) | YES | MUL |
wp_wc_order_addresses | first_name | text | YES | |
wp_wc_order_addresses | last_name | text | YES | |
wp_wc_order_addresses | company | text | YES | |
wp_wc_order_addresses | address_1 | text | YES | |
wp_wc_order_addresses | address_2 | text | YES | |
wp_wc_order_addresses | city | text | YES | |
wp_wc_order_addresses | state | text | YES | |
wp_wc_order_addresses | postcode | text | YES | |
wp_wc_order_addresses | country | text | YES | |
wp_wc_order_addresses | email | varchar(320) | YES | MUL |
wp_wc_order_addresses | phone | varchar(100) | YES | MUL |
wp_wc_order_coupon_lookup | order_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_coupon_lookup | coupon_id | bigint(20) | NO | PRI |
wp_wc_order_coupon_lookup | date_created | datetime | NO | MUL |
wp_wc_order_coupon_lookup | discount_amount | double | NO | |
wp_wc_order_operational_data | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_order_operational_data | order_id | bigint(20) unsigned | YES | UNI |
wp_wc_order_operational_data | created_via | varchar(100) | YES | |
wp_wc_order_operational_data | woocommerce_version | varchar(20) | YES | |
wp_wc_order_operational_data | prices_include_tax | tinyint(1) | YES | |
wp_wc_order_operational_data | coupon_usages_are_counted | tinyint(1) | YES | |
wp_wc_order_operational_data | download_permission_granted | tinyint(1) | YES | |
wp_wc_order_operational_data | cart_hash | varchar(100) | YES | |
wp_wc_order_operational_data | new_order_email_sent | tinyint(1) | YES | |
wp_wc_order_operational_data | order_key | varchar(100) | YES | MUL |
wp_wc_order_operational_data | order_stock_reduced | tinyint(1) | YES | |
wp_wc_order_operational_data | date_paid_gmt | datetime | YES | |
wp_wc_order_operational_data | date_completed_gmt | datetime | YES | |
wp_wc_order_operational_data | shipping_tax_amount | decimal(26,8) | YES | |
wp_wc_order_operational_data | shipping_total_amount | decimal(26,8) | YES | |
wp_wc_order_operational_data | discount_tax_amount | decimal(26,8) | YES | |
wp_wc_order_operational_data | discount_total_amount | decimal(26,8) | YES | |
wp_wc_order_operational_data | recorded_sales | tinyint(1) | YES | |
wp_wc_order_product_lookup | order_item_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_product_lookup | order_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_product_lookup | product_id | bigint(20) unsigned | NO | MUL |
wp_wc_order_product_lookup | variation_id | bigint(20) unsigned | NO | |
wp_wc_order_product_lookup | customer_id | bigint(20) unsigned | YES | MUL |
wp_wc_order_product_lookup | date_created | datetime | NO | MUL |
wp_wc_order_product_lookup | product_qty | int(11) | NO | |
wp_wc_order_product_lookup | product_net_revenue | double | NO | |
wp_wc_order_product_lookup | product_gross_revenue | double | NO | |
wp_wc_order_product_lookup | coupon_amount | double | NO | |
wp_wc_order_product_lookup | tax_amount | double | NO | |
wp_wc_order_product_lookup | shipping_amount | double | NO | |
wp_wc_order_product_lookup | shipping_tax_amount | double | NO | |
wp_wc_order_stats | order_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_stats | parent_id | bigint(20) unsigned | NO | |
wp_wc_order_stats | date_created | datetime | NO | MUL |
wp_wc_order_stats | date_created_gmt | datetime | NO | |
wp_wc_order_stats | date_paid | datetime | YES | MUL |
wp_wc_order_stats | date_completed | datetime | YES | MUL |
wp_wc_order_stats | num_items_sold | int(11) | NO | |
wp_wc_order_stats | total_sales | double | NO | |
wp_wc_order_stats | tax_total | double | NO | |
wp_wc_order_stats | shipping_total | double | NO | |
wp_wc_order_stats | net_total | double | NO | |
wp_wc_order_stats | returning_customer | tinyint(1) | YES | |
wp_wc_order_stats | status | varchar(20) | NO | MUL |
wp_wc_order_stats | customer_id | bigint(20) unsigned | NO | MUL |
wp_wc_order_stats | payment_method | varchar(100) | YES | MUL |
wp_wc_order_tax_lookup | order_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_tax_lookup | tax_rate_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_tax_lookup | order_item_id | bigint(20) unsigned | NO | PRI |
wp_wc_order_tax_lookup | date_created | datetime | NO | MUL |
wp_wc_order_tax_lookup | shipping_tax | double | NO | |
wp_wc_order_tax_lookup | order_tax | double | NO | |
wp_wc_order_tax_lookup | total_tax | double | NO | |
wp_wc_order_tax_lookup | taxable_amount | double | NO | |
wp_wc_order_tax_lookup | order_taxable_amount | double | YES | |
wp_wc_order_tax_lookup | shipping_taxable_amount | double | YES | |
wp_wc_product_attributes_lookup | product_id | bigint(20) unsigned | NO | PRI |
wp_wc_product_attributes_lookup | product_or_parent_id | bigint(20) unsigned | NO | PRI |
wp_wc_product_attributes_lookup | taxonomy | varchar(32) | NO | PRI |
wp_wc_product_attributes_lookup | term_id | bigint(20) unsigned | NO | PRI |
wp_wc_product_attributes_lookup | is_variation_attribute | tinyint(1) | NO | MUL |
wp_wc_product_attributes_lookup | in_stock | tinyint(1) | NO | |
wp_wc_product_download_directories | url_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_product_download_directories | url | varchar(256) | NO | MUL |
wp_wc_product_download_directories | enabled | tinyint(1) | NO | |
wp_wc_product_meta_lookup | product_id | bigint(20) unsigned | NO | PRI |
wp_wc_product_meta_lookup | sku | varchar(100) | YES | MUL |
wp_wc_product_meta_lookup | global_unique_id | varchar(100) | YES | MUL |
wp_wc_product_meta_lookup | virtual | tinyint(1) | YES | MUL |
wp_wc_product_meta_lookup | downloadable | tinyint(1) | YES | MUL |
wp_wc_product_meta_lookup | min_price | decimal(19,4) | YES | MUL |
wp_wc_product_meta_lookup | max_price | decimal(19,4) | YES | |
wp_wc_product_meta_lookup | onsale | tinyint(1) | YES | MUL |
wp_wc_product_meta_lookup | stock_quantity | double | YES | MUL |
wp_wc_product_meta_lookup | stock_status | varchar(100) | YES | MUL |
wp_wc_product_meta_lookup | rating_count | bigint(20) | YES | |
wp_wc_product_meta_lookup | average_rating | decimal(3,2) | YES | |
wp_wc_product_meta_lookup | total_sales | bigint(20) | YES | |
wp_wc_product_meta_lookup | tax_status | varchar(100) | YES | |
wp_wc_product_meta_lookup | tax_class | varchar(100) | YES | |
wp_wc_rate_limits | rate_limit_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_rate_limits | rate_limit_key | varchar(200) | NO | UNI |
wp_wc_rate_limits | rate_limit_expiry | bigint(20) unsigned | NO | |
wp_wc_rate_limits | rate_limit_remaining | smallint(10) | NO | |
wp_wc_reserved_stock | order_id | bigint(20) unsigned | NO | PRI |
wp_wc_reserved_stock | product_id | bigint(20) unsigned | NO | PRI |
wp_wc_reserved_stock | stock_quantity | double | NO | |
wp_wc_reserved_stock | timestamp | datetime | NO | |
wp_wc_reserved_stock | expires | datetime | NO | |
wp_wc_stock_notificationmeta | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_stock_notificationmeta | notification_id | bigint(20) unsigned | NO | MUL |
wp_wc_stock_notificationmeta | meta_key | varchar(255) | YES | MUL |
wp_wc_stock_notificationmeta | meta_value | longtext | YES | |
wp_wc_stock_notifications | id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_stock_notifications | product_id | bigint(20) unsigned | NO | MUL |
wp_wc_stock_notifications | user_id | bigint(20) unsigned | NO | MUL |
wp_wc_stock_notifications | user_email | varchar(100) | NO | MUL |
wp_wc_stock_notifications | status | varchar(20) | NO | |
wp_wc_stock_notifications | date_created_gmt | datetime | YES | |
wp_wc_stock_notifications | date_modified_gmt | datetime | YES | |
wp_wc_stock_notifications | date_confirmed_gmt | datetime | YES | |
wp_wc_stock_notifications | date_last_attempt_gmt | datetime | YES | |
wp_wc_stock_notifications | date_notified_gmt | datetime | YES | |
wp_wc_stock_notifications | date_cancelled_gmt | datetime | YES | |
wp_wc_stock_notifications | cancellation_source | varchar(30) | YES | |
wp_wc_tax_rate_classes | tax_rate_class_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_tax_rate_classes | name | varchar(200) | NO | |
wp_wc_tax_rate_classes | slug | varchar(200) | NO | UNI |
wp_wc_webhooks | webhook_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wc_webhooks | status | varchar(200) | NO | |
wp_wc_webhooks | name | text | NO | |
wp_wc_webhooks | user_id | bigint(20) unsigned | NO | MUL |
wp_wc_webhooks | delivery_url | text | NO | |
wp_wc_webhooks | secret | text | NO | |
wp_wc_webhooks | topic | varchar(200) | NO | |
wp_wc_webhooks | date_created | datetime | NO | |
wp_wc_webhooks | date_created_gmt | datetime | NO | |
wp_wc_webhooks | date_modified | datetime | NO | |
wp_wc_webhooks | date_modified_gmt | datetime | NO | |
wp_wc_webhooks | api_version | smallint(4) | NO | |
wp_wc_webhooks | failure_count | smallint(10) | NO | |
wp_wc_webhooks | pending_delivery | tinyint(1) | NO | |
wp_woocommerce_api_keys | key_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_api_keys | user_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_api_keys | description | varchar(200) | YES | |
wp_woocommerce_api_keys | permissions | varchar(10) | NO | |
wp_woocommerce_api_keys | consumer_key | char(64) | NO | MUL |
wp_woocommerce_api_keys | consumer_secret | char(43) | NO | MUL |
wp_woocommerce_api_keys | nonces | longtext | YES | |
wp_woocommerce_api_keys | truncated_key | char(7) | NO | |
wp_woocommerce_api_keys | last_access | datetime | YES | |
wp_woocommerce_attribute_taxonomies | attribute_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_attribute_taxonomies | attribute_name | varchar(200) | NO | MUL |
wp_woocommerce_attribute_taxonomies | attribute_label | varchar(200) | YES | |
wp_woocommerce_attribute_taxonomies | attribute_type | varchar(20) | NO | |
wp_woocommerce_attribute_taxonomies | attribute_orderby | varchar(20) | NO | |
wp_woocommerce_attribute_taxonomies | attribute_public | int(1) | NO | |
wp_woocommerce_downloadable_product_permissions | permission_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_downloadable_product_permissions | download_id | varchar(36) | NO | MUL |
wp_woocommerce_downloadable_product_permissions | product_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_downloadable_product_permissions | order_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_downloadable_product_permissions | order_key | varchar(200) | NO | |
wp_woocommerce_downloadable_product_permissions | user_email | varchar(200) | NO | MUL |
wp_woocommerce_downloadable_product_permissions | user_id | bigint(20) unsigned | YES | MUL |
wp_woocommerce_downloadable_product_permissions | downloads_remaining | varchar(9) | YES | |
wp_woocommerce_downloadable_product_permissions | access_granted | datetime | NO | |
wp_woocommerce_downloadable_product_permissions | access_expires | datetime | YES | |
wp_woocommerce_downloadable_product_permissions | download_count | bigint(20) unsigned | NO | |
wp_woocommerce_log | log_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_log | timestamp | datetime | NO | |
wp_woocommerce_log | level | smallint(4) | NO | MUL |
wp_woocommerce_log | source | varchar(200) | NO | |
wp_woocommerce_log | message | longtext | NO | |
wp_woocommerce_log | context | longtext | YES | |
wp_woocommerce_order_itemmeta | meta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_order_itemmeta | order_item_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_order_itemmeta | meta_key | varchar(255) | YES | MUL |
wp_woocommerce_order_itemmeta | meta_value | longtext | YES | |
wp_woocommerce_order_items | order_item_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_order_items | order_item_name | text | NO | |
wp_woocommerce_order_items | order_item_type | varchar(200) | NO | |
wp_woocommerce_order_items | order_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_payment_tokenmeta | meta_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_payment_tokenmeta | payment_token_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_payment_tokenmeta | meta_key | varchar(255) | YES | MUL |
wp_woocommerce_payment_tokenmeta | meta_value | longtext | YES | |
wp_woocommerce_payment_tokens | token_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_payment_tokens | gateway_id | varchar(20) | NO | |
wp_woocommerce_payment_tokens | token | text | NO | |
wp_woocommerce_payment_tokens | user_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_payment_tokens | type | varchar(20) | NO | |
wp_woocommerce_payment_tokens | is_default | tinyint(1) | NO | |
wp_woocommerce_sessions | session_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_sessions | session_key | char(32) | NO | UNI |
wp_woocommerce_sessions | session_value | longtext | NO | |
wp_woocommerce_sessions | session_expiry | bigint(20) unsigned | NO | MUL |
wp_woocommerce_shipping_zones | zone_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_shipping_zones | zone_name | varchar(200) | NO | |
wp_woocommerce_shipping_zones | zone_order | bigint(20) unsigned | NO | MUL |
wp_woocommerce_shipping_zone_locations | location_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_shipping_zone_locations | zone_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_shipping_zone_locations | location_code | varchar(200) | NO | MUL |
wp_woocommerce_shipping_zone_locations | location_type | varchar(40) | NO | MUL |
wp_woocommerce_shipping_zone_methods | zone_id | bigint(20) unsigned | NO | MUL |
wp_woocommerce_shipping_zone_methods | instance_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_shipping_zone_methods | method_id | varchar(200) | NO | MUL |
wp_woocommerce_shipping_zone_methods | method_order | bigint(20) unsigned | NO | |
wp_woocommerce_shipping_zone_methods | is_enabled | tinyint(1) | NO | |
wp_woocommerce_tax_rates | tax_rate_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_tax_rates | tax_rate_country | varchar(2) | NO | MUL |
wp_woocommerce_tax_rates | tax_rate_state | varchar(200) | NO | MUL |
wp_woocommerce_tax_rates | tax_rate | varchar(8) | NO | |
wp_woocommerce_tax_rates | tax_rate_name | varchar(200) | NO | |
wp_woocommerce_tax_rates | tax_rate_priority | bigint(20) unsigned | NO | MUL |
wp_woocommerce_tax_rates | tax_rate_compound | int(1) | NO | |
wp_woocommerce_tax_rates | tax_rate_shipping | int(1) | NO | |
wp_woocommerce_tax_rates | tax_rate_order | bigint(20) unsigned | NO | |
wp_woocommerce_tax_rates | tax_rate_class | varchar(200) | NO | MUL |
wp_woocommerce_tax_rate_locations | location_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_woocommerce_tax_rate_locations | location_code | varchar(200) | NO | MUL |
wp_woocommerce_tax_rate_locations | location_type | varchar(40) | NO | MUL |
wp_woocommerce_tax_rate_locations | tax_rate_id | bigint(20) unsigned | NO | MUL |
wp_wpvivid_options | option_id | bigint(20) unsigned | NO | PRI | auto_increment
wp_wpvivid_options | option_name | varchar(191) | NO | UNI |
wp_wpvivid_options | option_value | longtext | NO | |
```

---

## 7. Annexe B — Index de toutes les tables (437 index)

Export brut `information_schema.STATISTICS` groupé par index. Format : `table | index | unicité | colonnes` (UNIQUE = contrainte d'unicité, INDEX = index secondaire ; `PRIMARY` = clé primaire).

```
wp_actionscheduler_actions | args | INDEX | args
wp_actionscheduler_actions | claim_id_status_priority_scheduled_date_gmt | INDEX | claim_id,status,priority,scheduled_date_gmt
wp_actionscheduler_actions | group_id | INDEX | group_id
wp_actionscheduler_actions | hook_status_scheduled_date_gmt | INDEX | hook,status,scheduled_date_gmt
wp_actionscheduler_actions | last_attempt_gmt | INDEX | last_attempt_gmt
wp_actionscheduler_actions | PRIMARY | UNIQUE | action_id
wp_actionscheduler_actions | scheduled_date_gmt | INDEX | scheduled_date_gmt
wp_actionscheduler_actions | status_claim_id | INDEX | status,claim_id
wp_actionscheduler_actions | status_last_attempt_gmt | INDEX | status,last_attempt_gmt
wp_actionscheduler_actions | status_scheduled_date_gmt | INDEX | status,scheduled_date_gmt
wp_actionscheduler_claims | date_created_gmt | INDEX | date_created_gmt
wp_actionscheduler_claims | PRIMARY | UNIQUE | claim_id
wp_actionscheduler_groups | PRIMARY | UNIQUE | group_id
wp_actionscheduler_groups | slug | INDEX | slug
wp_actionscheduler_logs | action_id | INDEX | action_id
wp_actionscheduler_logs | log_date_gmt | INDEX | log_date_gmt
wp_actionscheduler_logs | PRIMARY | UNIQUE | log_id
wp_akd_catalog | PRIMARY | UNIQUE | id
wp_akd_catalog | sku | UNIQUE | sku
wp_akd_orders | external_id | UNIQUE | external_id
wp_akd_orders | PRIMARY | UNIQUE | wc_id
wp_allovente_myfusion_catalogue | brand_name | INDEX | brand_name
wp_allovente_myfusion_catalogue | category_name | INDEX | category_name
wp_allovente_myfusion_catalogue | PRIMARY | UNIQUE | product_id
wp_allovente_myfusion_catalogue | selected | INDEX | selected
wp_allovente_sales_funnel | PRIMARY | UNIQUE | event_day,event_name,device
wp_cmplz_cookiebanners | PRIMARY | UNIQUE | ID
wp_cmplz_cookies | PRIMARY | UNIQUE | ID
wp_cmplz_dnsmpd | PRIMARY | UNIQUE | ID
wp_cmplz_services | PRIMARY | UNIQUE | ID
wp_commentmeta | comment_id | INDEX | comment_id
wp_commentmeta | meta_key | INDEX | meta_key
wp_commentmeta | PRIMARY | UNIQUE | meta_id
wp_comments | comment_approved_date_gmt | INDEX | comment_approved,comment_date_gmt
wp_comments | comment_author_email | INDEX | comment_author_email
wp_comments | comment_date_gmt | INDEX | comment_date_gmt
wp_comments | comment_parent | INDEX | comment_parent
wp_comments | comment_post_ID | INDEX | comment_post_ID
wp_comments | PRIMARY | UNIQUE | comment_ID
wp_comments | woo_idx_comment_approved_type | INDEX | comment_approved,comment_type,comment_post_ID
wp_comments | woo_idx_comment_date_type | INDEX | comment_date_gmt,comment_type,comment_approved,comment_post_ID
wp_comments | woo_idx_comment_type | INDEX | comment_type
wp_e_events | created_at_index | INDEX | created_at
wp_e_events | PRIMARY | UNIQUE | id
wp_frmt_form_entry | entry_form_custom_id | INDEX | form_id,custom_id
wp_frmt_form_entry | entry_form_id | INDEX | form_id
wp_frmt_form_entry | entry_form_status | INDEX | form_id,status
wp_frmt_form_entry | entry_is_spam | INDEX | is_spam
wp_frmt_form_entry | entry_status | INDEX | status
wp_frmt_form_entry | entry_type | INDEX | entry_type
wp_frmt_form_entry | PRIMARY | UNIQUE | entry_id
wp_frmt_form_entry_meta | meta_entry_id | INDEX | entry_id
wp_frmt_form_entry_meta | meta_key | INDEX | meta_key
wp_frmt_form_entry_meta | meta_key_object | INDEX | entry_id,meta_key
wp_frmt_form_entry_meta | PRIMARY | UNIQUE | meta_id
wp_frmt_form_reports | PRIMARY | UNIQUE | report_id
wp_frmt_form_views | PRIMARY | UNIQUE | view_id
wp_frmt_form_views | view_form_id | INDEX | form_id
wp_frmt_form_views | view_form_object | INDEX | form_id,view_id
wp_frmt_form_views | view_form_object_ip | INDEX | form_id,view_id,ip
wp_frmt_form_views | view_ip | INDEX | ip
wp_fsmpt_email_logs | created_at_status | INDEX | created_at,status
wp_fsmpt_email_logs | PRIMARY | UNIQUE | id
wp_gla_attribute_mapping_rules | PRIMARY | UNIQUE | id
wp_gla_budget_recommendations | country_currency | UNIQUE | country,currency
wp_gla_budget_recommendations | PRIMARY | UNIQUE | id
wp_gla_merchant_issues | PRIMARY | UNIQUE | id
wp_gla_merchant_price_benchmarks | mc_insights_effectiveness | INDEX | mc_insights_effectiveness
wp_gla_merchant_price_benchmarks | mc_product_id | UNIQUE | mc_product_id
wp_gla_merchant_price_benchmarks | price_compared_with_benchmark | INDEX | price_compared_with_benchmark
wp_gla_merchant_price_benchmarks | PRIMARY | UNIQUE | product_id
wp_gla_shipping_rates | country | INDEX | country
wp_gla_shipping_rates | currency | INDEX | currency
wp_gla_shipping_rates | PRIMARY | UNIQUE | id
wp_gla_shipping_times | country | INDEX | country
wp_gla_shipping_times | PRIMARY | UNIQUE | id
wp_independent_analytics_campaigns | landing_page_id | INDEX | landing_page_id
wp_independent_analytics_campaigns | PRIMARY | UNIQUE | campaign_id
wp_independent_analytics_campaigns | utm_campaign_id | INDEX | utm_campaign_id
wp_independent_analytics_campaigns | utm_medium_id | INDEX | utm_medium_id
wp_independent_analytics_campaigns | utm_source_id | INDEX | utm_source_id
wp_independent_analytics_campaign_urls | PRIMARY | UNIQUE | campaign_url_id
wp_independent_analytics_cities | cities_unique_index | UNIQUE | country_id,subdivision,city
wp_independent_analytics_cities | PRIMARY | UNIQUE | city_id
wp_independent_analytics_clicked_links | link_id | INDEX | link_id
wp_independent_analytics_clicked_links | PRIMARY | UNIQUE | click_id,link_id
wp_independent_analytics_clicks | PRIMARY | UNIQUE | click_id
wp_independent_analytics_clicks | view_id | INDEX | view_id
wp_independent_analytics_click_targets | PRIMARY | UNIQUE | click_target_id
wp_independent_analytics_countries | countries_unique_index | UNIQUE | country_code,country,continent
wp_independent_analytics_countries | PRIMARY | UNIQUE | country_id
wp_independent_analytics_device_browsers | device_browser | UNIQUE | device_browser
wp_independent_analytics_device_browsers | PRIMARY | UNIQUE | device_browser_id
wp_independent_analytics_device_oss | device_os | UNIQUE | device_os
wp_independent_analytics_device_oss | PRIMARY | UNIQUE | device_os_id
wp_independent_analytics_device_types | device_type | UNIQUE | device_type
wp_independent_analytics_device_types | PRIMARY | UNIQUE | device_type_id
wp_independent_analytics_forms | plugin_id | UNIQUE | plugin_id,plugin_form_id
wp_independent_analytics_forms | PRIMARY | UNIQUE | form_id
wp_independent_analytics_form_submissions | PRIMARY | UNIQUE | form_submission_id
wp_independent_analytics_landing_pages | PRIMARY | UNIQUE | id
wp_independent_analytics_links | click_target_id | INDEX | click_target_id
wp_independent_analytics_links | link_rule_id | INDEX | link_rule_id
wp_independent_analytics_links | link_rule_id_2 | UNIQUE | link_rule_id,click_target_id
wp_independent_analytics_links | PRIMARY | UNIQUE | id
wp_independent_analytics_link_rules | PRIMARY | UNIQUE | link_rule_id
wp_independent_analytics_orders | created_at | INDEX | created_at
wp_independent_analytics_orders | edd_order_id | UNIQUE | edd_order_id
wp_independent_analytics_orders | fluent_cart_order_id | UNIQUE | fluent_cart_order_id
wp_independent_analytics_orders | initial_view_id | INDEX | initial_view_id
wp_independent_analytics_orders | orders_surecart_order_id_index | UNIQUE | surecart_order_id
wp_independent_analytics_orders | orders_woocommerce_order_id_index | UNIQUE | woocommerce_order_id
wp_independent_analytics_orders | pmpro_order_id | UNIQUE | pmpro_order_id
wp_independent_analytics_orders | PRIMARY | UNIQUE | order_id
wp_independent_analytics_orders | view_id | INDEX | view_id
wp_independent_analytics_referrers | PRIMARY | UNIQUE | id
wp_independent_analytics_referrers | referrers_domain_index | UNIQUE | domain
wp_independent_analytics_referrers | referrer_type_id | INDEX | referrer_type_id
wp_independent_analytics_referrer_types | PRIMARY | UNIQUE | id
wp_independent_analytics_referrer_types | referrer_type | UNIQUE | referrer_type
wp_independent_analytics_reports | PRIMARY | UNIQUE | report_id
wp_independent_analytics_resources | cached_author_id | INDEX | cached_author_id
wp_independent_analytics_resources | PRIMARY | UNIQUE | id
wp_independent_analytics_sessions | campaign_id | INDEX | campaign_id
wp_independent_analytics_sessions | city_id | INDEX | city_id
wp_independent_analytics_sessions | country_id | INDEX | country_id
wp_independent_analytics_sessions | device_browser_id | INDEX | device_browser_id
wp_independent_analytics_sessions | device_os_id | INDEX | device_os_id
wp_independent_analytics_sessions | device_type_id | INDEX | device_type_id
wp_independent_analytics_sessions | initial_view_id | INDEX | initial_view_id
wp_independent_analytics_sessions | new_bigint_visitor_id | INDEX | visitor_id
wp_independent_analytics_sessions | PRIMARY | UNIQUE | session_id
wp_independent_analytics_sessions | referrer_id | INDEX | referrer_id
wp_independent_analytics_sessions | sessions_campaign_summary_index | UNIQUE | created_at,session_id,visitor_id,campaign_id,total_views
wp_independent_analytics_sessions | sessions_city_summary_index | UNIQUE | created_at,session_id,visitor_id,city_id,total_views
wp_independent_analytics_sessions | sessions_country_summary_index | UNIQUE | created_at,session_id,visitor_id,country_id,total_views
wp_independent_analytics_sessions | sessions_created_at_index | INDEX | created_at
wp_independent_analytics_sessions | sessions_device_browser_summary_index | UNIQUE | created_at,session_id,visitor_id,device_browser_id,total_views
wp_independent_analytics_sessions | sessions_device_os_summary_index | UNIQUE | created_at,session_id,visitor_id,device_os_id,total_views
wp_independent_analytics_sessions | sessions_device_type_summary_index | UNIQUE | created_at,session_id,visitor_id,device_type_id,total_views
wp_independent_analytics_sessions | sessions_summary_index | UNIQUE | created_at,session_id,visitor_id,referrer_id,total_views
wp_independent_analytics_utm_campaigns | PRIMARY | UNIQUE | id
wp_independent_analytics_utm_mediums | PRIMARY | UNIQUE | id
wp_independent_analytics_utm_sources | PRIMARY | UNIQUE | id
wp_independent_analytics_views | PRIMARY | UNIQUE | id
wp_independent_analytics_views | session_id | INDEX | session_id
wp_independent_analytics_views | session_id_2 | INDEX | session_id,viewed_at
wp_independent_analytics_views | views_resource_id_index | INDEX | resource_id
wp_independent_analytics_views | views_summary_index | INDEX | session_id,viewed_at,resource_id
wp_independent_analytics_views | views_viewed_at_index | INDEX | viewed_at
wp_independent_analytics_visitors | hash | UNIQUE | hash
wp_independent_analytics_visitors | PRIMARY | UNIQUE | visitor_id
wp_independent_analytics_wc_orders | initial_view_id | INDEX | initial_view_id
wp_independent_analytics_wc_orders | PRIMARY | UNIQUE | order_id
wp_independent_analytics_wc_orders | wc_orders_created_at_index | INDEX | created_at
wp_independent_analytics_wc_orders | wc_orders_view_id_index | INDEX | view_id
wp_keybin_logs | PRIMARY | UNIQUE | id
wp_links | link_visible | INDEX | link_visible
wp_links | PRIMARY | UNIQUE | link_id
wp_mwai_filemeta | PRIMARY | UNIQUE | meta_id
wp_mwai_files | PRIMARY | UNIQUE | id
wp_mwai_files | unique_file_id | UNIQUE | refId
wp_mwai_tasklogs | PRIMARY | UNIQUE | id
wp_mwai_tasklogs | task_id_started | INDEX | task_id,started
wp_mwai_tasks | category | INDEX | category
wp_mwai_tasks | expires | INDEX | expires_at
wp_mwai_tasks | PRIMARY | UNIQUE | id
wp_mwai_tasks | status_next | INDEX | status,next_run
wp_mwai_tasks | task_name | UNIQUE | task_name
wp_options | autoload | INDEX | autoload
wp_options | option_name | UNIQUE | option_name
wp_options | PRIMARY | UNIQUE | option_id
wp_packlink_entity | PRIMARY | UNIQUE | id
wp_pmxi_files | PRIMARY | UNIQUE | id
wp_pmxi_hash | PRIMARY | UNIQUE | hash
wp_pmxi_history | PRIMARY | UNIQUE | id
wp_pmxi_images | PRIMARY | UNIQUE | id
wp_pmxi_imports | PRIMARY | UNIQUE | id
wp_pmxi_posts | PRIMARY | UNIQUE | id
wp_pmxi_templates | PRIMARY | UNIQUE | id
wp_postmeta | allovente_key_value | INDEX | meta_key,meta_value
wp_postmeta | allovente_post_key | INDEX | post_id,meta_key
wp_postmeta | meta_key | INDEX | meta_key
wp_postmeta | post_id | INDEX | post_id
wp_postmeta | PRIMARY | UNIQUE | meta_id
wp_posts | post_author | INDEX | post_author
wp_posts | post_name | INDEX | post_name
wp_posts | post_parent | INDEX | post_parent
wp_posts | PRIMARY | UNIQUE | ID
wp_posts | type_status_author | INDEX | post_type,post_status,post_author
wp_posts | type_status_date | INDEX | post_type,post_status,post_date,ID
wp_rank_math_analytics_gsc | analytics_page | INDEX | page
wp_rank_math_analytics_gsc | analytics_query | INDEX | query
wp_rank_math_analytics_gsc | clicks | INDEX | clicks
wp_rank_math_analytics_gsc | PRIMARY | UNIQUE | id
wp_rank_math_analytics_gsc | rank_position | INDEX | position
wp_rank_math_analytics_inspections | analytics_object_page | INDEX | page
wp_rank_math_analytics_inspections | created | INDEX | created
wp_rank_math_analytics_inspections | index_verdict | INDEX | index_verdict
wp_rank_math_analytics_inspections | page_fetch_state | INDEX | page_fetch_state
wp_rank_math_analytics_inspections | PRIMARY | UNIQUE | id
wp_rank_math_analytics_inspections | rich_results_verdict | INDEX | rich_results_verdict
wp_rank_math_analytics_inspections | robots_txt_state | INDEX | robots_txt_state
wp_rank_math_analytics_objects | analytics_object_page | INDEX | page
wp_rank_math_analytics_objects | PRIMARY | UNIQUE | id
wp_rank_math_internal_links | link_direction | INDEX | post_id,type
wp_rank_math_internal_links | PRIMARY | UNIQUE | id
wp_rank_math_internal_links | target_post_id | INDEX | target_post_id
wp_rank_math_internal_meta | PRIMARY | UNIQUE | object_id
wp_redirection_404 | created | INDEX | created
wp_redirection_404 | ip | INDEX | ip
wp_redirection_404 | PRIMARY | UNIQUE | id
wp_redirection_404 | referrer | INDEX | referrer
wp_redirection_groups | module_id | INDEX | module_id
wp_redirection_groups | PRIMARY | UNIQUE | id
wp_redirection_groups | status | INDEX | status
wp_redirection_items | group | INDEX | group_id
wp_redirection_items | group_idpos | INDEX | group_id,position
wp_redirection_items | match_url | INDEX | match_url
wp_redirection_items | PRIMARY | UNIQUE | id
wp_redirection_items | regex | INDEX | regex
wp_redirection_items | status | INDEX | status
wp_redirection_items | url | INDEX | url
wp_redirection_logs | created | INDEX | created
wp_redirection_logs | ip | INDEX | ip
wp_redirection_logs | PRIMARY | UNIQUE | id
wp_redirection_logs | redirection_id | INDEX | redirection_id
wp_snippets | active | INDEX | active
wp_snippets | PRIMARY | UNIQUE | id
wp_snippets | scope | INDEX | scope
wp_srfm_entries | idx_form_id | INDEX | form_id
wp_srfm_entries | idx_form_id_created_at_status | INDEX | form_id,created_at,status
wp_srfm_entries | idx_user_id | INDEX | user_id
wp_srfm_entries | PRIMARY | UNIQUE | ID
wp_srfm_payments | PRIMARY | UNIQUE | id
wp_surecart_incoming_webhooks | created_at | INDEX | created_at
wp_surecart_incoming_webhooks | PRIMARY | UNIQUE | id
wp_surecart_incoming_webhooks | processed_at | INDEX | processed_at
wp_surecart_incoming_webhooks | updated_at | INDEX | updated_at
wp_surecart_incoming_webhooks | webhook_id | INDEX | webhook_id
wp_surecart_integrations | created_at | INDEX | created_at
wp_surecart_integrations | integration_id | INDEX | integration_id
wp_surecart_integrations | model_id | INDEX | model_id
wp_surecart_integrations | PRIMARY | UNIQUE | id
wp_surecart_integrations | updated_at | INDEX | updated_at
wp_surecart_variant_option_values | account_id | INDEX | account_id
wp_surecart_variant_option_values | created_at | INDEX | created_at
wp_surecart_variant_option_values | name | INDEX | name
wp_surecart_variant_option_values | post_id | INDEX | post_id
wp_surecart_variant_option_values | PRIMARY | UNIQUE | id
wp_surecart_variant_option_values | product_id | INDEX | product_id
wp_surecart_variant_option_values | updated_at | INDEX | updated_at
wp_surecart_variant_option_values | value | INDEX | value
wp_surecookie_consent_log | action | INDEX | action
wp_surecookie_consent_log | geo_preset_id | INDEX | geo_preset_id
wp_surecookie_consent_log | ip_address | INDEX | ip_address
wp_surecookie_consent_log | is_forwarded | INDEX | is_forwarded
wp_surecookie_consent_log | PRIMARY | UNIQUE | id
wp_surecookie_consent_log | session_unique | UNIQUE | session_id,timestamp
wp_surecookie_consent_log | timestamp | INDEX | timestamp
wp_surecookie_consent_log | user_id | INDEX | user_id
wp_suretriggers_webhook_requests | PRIMARY | UNIQUE | id
wp_termmeta | meta_key | INDEX | meta_key
wp_termmeta | PRIMARY | UNIQUE | meta_id
wp_termmeta | term_id | INDEX | term_id
wp_terms | name | INDEX | name
wp_terms | PRIMARY | UNIQUE | term_id
wp_terms | slug | INDEX | slug
wp_term_relationships | PRIMARY | UNIQUE | object_id,term_taxonomy_id
wp_term_relationships | term_taxonomy_id | INDEX | term_taxonomy_id
wp_term_taxonomy | PRIMARY | UNIQUE | term_taxonomy_id
wp_term_taxonomy | taxonomy | INDEX | taxonomy
wp_term_taxonomy | term_id_taxonomy | UNIQUE | term_id,taxonomy
wp_trp_dictionary_fr_fr_en_us | block_type | INDEX | block_type
wp_trp_dictionary_fr_fr_en_us | id | UNIQUE | id
wp_trp_dictionary_fr_fr_en_us | index_name | INDEX | original
wp_trp_dictionary_fr_fr_en_us | original_fulltext | INDEX | original
wp_trp_dictionary_fr_fr_en_us | PRIMARY | UNIQUE | id
wp_trp_gettext_en_us | gettext_original_plural_unique | UNIQUE | original_id,plural_form
wp_trp_gettext_en_us | id | UNIQUE | id
wp_trp_gettext_en_us | index_name | INDEX | original
wp_trp_gettext_en_us | original_fulltext | INDEX | original
wp_trp_gettext_en_us | PRIMARY | UNIQUE | id
wp_trp_gettext_fr_fr | gettext_original_plural_unique | UNIQUE | original_id,plural_form
wp_trp_gettext_fr_fr | id | UNIQUE | id
wp_trp_gettext_fr_fr | index_name | INDEX | original
wp_trp_gettext_fr_fr | original_fulltext | INDEX | original
wp_trp_gettext_fr_fr | PRIMARY | UNIQUE | id
wp_trp_gettext_original_meta | gettext_index_original_id | INDEX | original_id
wp_trp_gettext_original_meta | gettext_meta_key | INDEX | meta_key
wp_trp_gettext_original_meta | meta_id | UNIQUE | meta_id
wp_trp_gettext_original_meta | PRIMARY | UNIQUE | meta_id
wp_trp_gettext_original_strings | gettext_index_original | INDEX | original
wp_trp_gettext_original_strings | gettext_lookup_hash_unique | UNIQUE | lookup_hash
wp_trp_gettext_original_strings | gettext_lookup_original_domain_context | INDEX | original,domain,context
wp_trp_gettext_original_strings | PRIMARY | UNIQUE | id
wp_trp_original_meta | index_original_id | INDEX | original_id
wp_trp_original_meta | meta_id | UNIQUE | meta_id
wp_trp_original_meta | meta_key | INDEX | meta_key
wp_trp_original_meta | PRIMARY | UNIQUE | meta_id
wp_trp_original_strings | index_original | INDEX | original
wp_trp_original_strings | id | UNIQUE | id
wp_trp_original_strings | PRIMARY | UNIQUE | id
wp_usermeta | meta_key | INDEX | meta_key
wp_usermeta | PRIMARY | UNIQUE | umeta_id
wp_usermeta | user_id | INDEX | user_id
wp_users | PRIMARY | UNIQUE | ID
wp_users | user_email | INDEX | user_email
wp_users | user_login_key | INDEX | user_login
wp_users | user_nicename | INDEX | user_nicename
wp_wcpdf_invoice_number | order_id | INDEX | order_id
wp_wcpdf_invoice_number | PRIMARY | UNIQUE | id
wp_wcpdf_packing_slip_number | order_id | INDEX | order_id
wp_wcpdf_packing_slip_number | PRIMARY | UNIQUE | id
wp_wc_admin_notes | PRIMARY | UNIQUE | note_id
wp_wc_admin_note_actions | note_id | INDEX | note_id
wp_wc_admin_note_actions | PRIMARY | UNIQUE | action_id
wp_wc_category_lookup | PRIMARY | UNIQUE | category_tree_id,category_id
wp_wc_customer_lookup | email | INDEX | email
wp_wc_customer_lookup | PRIMARY | UNIQUE | customer_id
wp_wc_customer_lookup | user_id | UNIQUE | user_id
wp_wc_download_log | permission_id | INDEX | permission_id
wp_wc_download_log | PRIMARY | UNIQUE | download_log_id
wp_wc_download_log | timestamp | INDEX | timestamp
wp_wc_orders | billing_email | INDEX | billing_email
wp_wc_orders | customer_id_billing_email | INDEX | customer_id,billing_email
wp_wc_orders | customer_id_status | INDEX | customer_id,status
wp_wc_orders | date_created | INDEX | date_created_gmt
wp_wc_orders | date_updated | INDEX | date_updated_gmt
wp_wc_orders | parent_order_id | INDEX | parent_order_id
wp_wc_orders | PRIMARY | UNIQUE | id
wp_wc_orders | status | INDEX | status
wp_wc_orders | transaction_id | INDEX | transaction_id
wp_wc_orders | type_status_date | INDEX | type,status,date_created_gmt
wp_wc_orders_meta | meta_key_value | INDEX | meta_key,meta_value
wp_wc_orders_meta | order_id_meta_key_meta_value | INDEX | order_id,meta_key,meta_value
wp_wc_orders_meta | PRIMARY | UNIQUE | id
wp_wc_order_addresses | address_type_order_id | UNIQUE | address_type,order_id
wp_wc_order_addresses | email | INDEX | email
wp_wc_order_addresses | order_id | INDEX | order_id
wp_wc_order_addresses | phone | INDEX | phone
wp_wc_order_addresses | PRIMARY | UNIQUE | id
wp_wc_order_coupon_lookup | coupon_id | INDEX | coupon_id
wp_wc_order_coupon_lookup | date_created | INDEX | date_created
wp_wc_order_coupon_lookup | PRIMARY | UNIQUE | order_id,coupon_id
wp_wc_order_operational_data | order_id | UNIQUE | order_id
wp_wc_order_operational_data | order_key | INDEX | order_key
wp_wc_order_operational_data | PRIMARY | UNIQUE | id
wp_wc_order_product_lookup | customer_id | INDEX | customer_id
wp_wc_order_product_lookup | customer_product_date | INDEX | customer_id,product_id,date_created
wp_wc_order_product_lookup | date_created | INDEX | date_created
wp_wc_order_product_lookup | order_id | INDEX | order_id
wp_wc_order_product_lookup | PRIMARY | UNIQUE | order_item_id,order_id
wp_wc_order_product_lookup | product_id | INDEX | product_id
wp_wc_order_stats | customer_id | INDEX | customer_id
wp_wc_order_stats | date_created | INDEX | date_created
wp_wc_order_stats | idx_date_paid_status_parent | INDEX | date_paid,status,parent_id
wp_wc_order_stats | idx_payment_method_date_paid_status | INDEX | payment_method,date_paid,status
wp_wc_order_stats | PRIMARY | UNIQUE | order_id
wp_wc_order_stats | status | INDEX | status
wp_wc_order_tax_lookup | date_created | INDEX | date_created
wp_wc_order_tax_lookup | PRIMARY | UNIQUE | order_id,tax_rate_id,order_item_id
wp_wc_order_tax_lookup | tax_rate_id | INDEX | tax_rate_id
wp_wc_product_attributes_lookup | is_variation_attribute_term_id | INDEX | is_variation_attribute,term_id
wp_wc_product_attributes_lookup | PRIMARY | UNIQUE | product_or_parent_id,term_id,product_id,taxonomy
wp_wc_product_attributes_lookup | product_id | INDEX | product_id
wp_wc_product_attributes_lookup | taxonomy_term_id_in_stock_product_or_parent_id | INDEX | taxonomy,term_id,in_stock,product_or_parent_id
wp_wc_product_download_directories | PRIMARY | UNIQUE | url_id
wp_wc_product_download_directories | url | INDEX | url
wp_wc_product_meta_lookup | downloadable | INDEX | downloadable
wp_wc_product_meta_lookup | global_unique_id | INDEX | global_unique_id
wp_wc_product_meta_lookup | min_max_price | INDEX | min_price,max_price
wp_wc_product_meta_lookup | onsale | INDEX | onsale
wp_wc_product_meta_lookup | PRIMARY | UNIQUE | product_id
wp_wc_product_meta_lookup | sku | INDEX | sku
wp_wc_product_meta_lookup | stock_quantity | INDEX | stock_quantity
wp_wc_product_meta_lookup | stock_status | INDEX | stock_status
wp_wc_product_meta_lookup | virtual | INDEX | virtual
wp_wc_rate_limits | PRIMARY | UNIQUE | rate_limit_id
wp_wc_rate_limits | rate_limit_key | UNIQUE | rate_limit_key
wp_wc_reserved_stock | PRIMARY | UNIQUE | order_id,product_id
wp_wc_reserved_stock | product_id_expires | INDEX | product_id,expires
wp_wc_stock_notificationmeta | meta_key | INDEX | meta_key
wp_wc_stock_notificationmeta | notification_id | INDEX | notification_id
wp_wc_stock_notificationmeta | PRIMARY | UNIQUE | id
wp_wc_stock_notifications | email_lookup | INDEX | user_email,product_id,status
wp_wc_stock_notifications | PRIMARY | UNIQUE | id
wp_wc_stock_notifications | product_status_attempt | INDEX | product_id,status,date_last_attempt_gmt,id
wp_wc_stock_notifications | user_lookup | INDEX | user_id,product_id,status
wp_wc_tax_rate_classes | PRIMARY | UNIQUE | tax_rate_class_id
wp_wc_tax_rate_classes | slug | UNIQUE | slug
wp_wc_webhooks | PRIMARY | UNIQUE | webhook_id
wp_wc_webhooks | user_id | INDEX | user_id
wp_woocommerce_api_keys | consumer_key | INDEX | consumer_key
wp_woocommerce_api_keys | consumer_secret | INDEX | consumer_secret
wp_woocommerce_api_keys | PRIMARY | UNIQUE | key_id
wp_woocommerce_attribute_taxonomies | attribute_name | INDEX | attribute_name
wp_woocommerce_attribute_taxonomies | PRIMARY | UNIQUE | attribute_id
wp_woocommerce_downloadable_product_permissions | download_order_key_product | INDEX | product_id,order_id,order_key,download_id
wp_woocommerce_downloadable_product_permissions | download_order_product | INDEX | download_id,order_id,product_id
wp_woocommerce_downloadable_product_permissions | idx_user_email | INDEX | user_email
wp_woocommerce_downloadable_product_permissions | order_id | INDEX | order_id
wp_woocommerce_downloadable_product_permissions | PRIMARY | UNIQUE | permission_id
wp_woocommerce_downloadable_product_permissions | user_order_remaining_expires | INDEX | user_id,order_id,downloads_remaining,access_expires
wp_woocommerce_log | level | INDEX | level
wp_woocommerce_log | PRIMARY | UNIQUE | log_id
wp_woocommerce_order_itemmeta | meta_key | INDEX | meta_key
wp_woocommerce_order_itemmeta | order_item_id | INDEX | order_item_id
wp_woocommerce_order_itemmeta | PRIMARY | UNIQUE | meta_id
wp_woocommerce_order_items | order_id | INDEX | order_id
wp_woocommerce_order_items | PRIMARY | UNIQUE | order_item_id
wp_woocommerce_payment_tokenmeta | meta_key | INDEX | meta_key
wp_woocommerce_payment_tokenmeta | payment_token_id | INDEX | payment_token_id
wp_woocommerce_payment_tokenmeta | PRIMARY | UNIQUE | meta_id
wp_woocommerce_payment_tokens | PRIMARY | UNIQUE | token_id
wp_woocommerce_payment_tokens | user_id | INDEX | user_id
wp_woocommerce_sessions | PRIMARY | UNIQUE | session_id
wp_woocommerce_sessions | session_expiry | INDEX | session_expiry
wp_woocommerce_sessions | session_key | UNIQUE | session_key
wp_woocommerce_shipping_zones | PRIMARY | UNIQUE | zone_id
wp_woocommerce_shipping_zones | zone_order_id | INDEX | zone_order,zone_id
wp_woocommerce_shipping_zone_locations | location_type_code | INDEX | location_type,location_code
wp_woocommerce_shipping_zone_locations | PRIMARY | UNIQUE | location_id
wp_woocommerce_shipping_zone_locations | zone_id | INDEX | zone_id
wp_woocommerce_shipping_zone_methods | method_id | INDEX | method_id
wp_woocommerce_shipping_zone_methods | PRIMARY | UNIQUE | instance_id
wp_woocommerce_shipping_zone_methods | zone_id | INDEX | zone_id
wp_woocommerce_tax_rates | PRIMARY | UNIQUE | tax_rate_id
wp_woocommerce_tax_rates | tax_rate_class | INDEX | tax_rate_class
wp_woocommerce_tax_rates | tax_rate_country | INDEX | tax_rate_country
wp_woocommerce_tax_rates | tax_rate_priority | INDEX | tax_rate_priority
wp_woocommerce_tax_rates | tax_rate_state | INDEX | tax_rate_state
wp_woocommerce_tax_rate_locations | location_type_code | INDEX | location_type,location_code
wp_woocommerce_tax_rate_locations | PRIMARY | UNIQUE | location_id
wp_woocommerce_tax_rate_locations | tax_rate_id | INDEX | tax_rate_id
wp_wpvivid_options | option_name | UNIQUE | option_name
wp_wpvivid_options | PRIMARY | UNIQUE | option_id
```

---

## 8. Comment régénérer ce document

Depuis Vibe, via la passerelle (déploiement `allovente-ssh-gateway`) :

```bash
# schéma DDL complet
sudo -n mariadb-dump --no-data --skip-comments --compact wordpress > ~/allovente-db-schema.sql
# inventaire + comptages exacts + colonnes + index
sudo -n mariadb -N -e "SELECT TABLE_NAME, ENGINE, TABLE_ROWS, ROUND((DATA_LENGTH+INDEX_LENGTH)/1024/1024,2) FROM information_schema.TABLES WHERE TABLE_SCHEMA='wordpress' ORDER BY TABLE_NAME;"
sudo -n mariadb -N -e "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='wordpress' ORDER BY TABLE_NAME, ORDINAL_POSITION;"
sudo -n mariadb -N -e "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='wordpress' GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE ORDER BY TABLE_NAME, INDEX_NAME;"
# comptage exact par table
for t in $(sudo -n mariadb -N -e "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='wordpress' AND TABLE_TYPE='BASE TABLE'"); do echo "$t $(sudo -n mariadb -N wordpress -e "SELECT COUNT(*) FROM $t")"; done
```

Historique complémentaire : `~/allovente-docs/KNOWLEDGE.md` (référence), `~/ALLOVENTE-INTERVENTION-20261015.md`, `~/ALLOVENTE-PLAN-CORRECTIONS-20261015.md`, `git log` du dépôt, `list_executions` des workflows `allovente-ssh` / `allovente-read-file`.

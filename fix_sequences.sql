SELECT setval('gestion_affectation_id_seq', COALESCE((SELECT MAX(id) FROM gestion_affectation), 1));
SELECT setval('auth_user_id_seq', COALESCE((SELECT MAX(id) FROM auth_user), 1));
SELECT setval('auth_group_id_seq', COALESCE((SELECT MAX(id) FROM auth_group), 1));
SELECT setval('auth_permission_id_seq', COALESCE((SELECT MAX(id) FROM auth_permission), 1));
SELECT setval('django_content_type_id_seq', COALESCE((SELECT MAX(id) FROM django_content_type), 1));
SELECT setval('django_migrations_id_seq', COALESCE((SELECT MAX(id) FROM django_migrations), 1));
SELECT setval('gestion_agent_id_seq', COALESCE((SELECT MAX(id) FROM gestion_agent), 1));
SELECT setval('gestion_chauffeur_id_seq', COALESCE((SELECT MAX(id) FROM gestion_chauffeur), 1));
SELECT setval('gestion_course_id_seq', COALESCE((SELECT MAX(id) FROM gestion_course), 1));
SELECT setval('gestion_reservation_id_seq', COALESCE((SELECT MAX(id) FROM gestion_reservation), 1));
SELECT setval('gestion_societe_id_seq', COALESCE((SELECT MAX(id) FROM gestion_societe), 1));
SELECT setval('gestion_heuretransport_id_seq', COALESCE((SELECT MAX(id) FROM gestion_heuretransport), 1));
SELECT setval('gestion_notificationadmin_id_seq', COALESCE((SELECT MAX(id) FROM gestion_notificationadmin), 1));
SELECT setval('chauffeurs_mobile_mobilecoursestatus_id_seq', COALESCE((SELECT MAX(id) FROM chauffeurs_mobile_mobilecoursestatus), 1));
SELECT setval('chauffeurs_mobile_mobilenotification_id_seq', COALESCE((SELECT MAX(id) FROM chauffeurs_mobile_mobilenotification), 1));

SELECT '✅ Toutes les séquences ont été corrigées !' as result;
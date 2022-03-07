truncate public.core_practice cascade;


INSERT INTO public.core_practice (created_at,modified_at,id,"name",industry,created_by_id,modified_by_id,active) VALUES
	 ('2022-02-07 13:40:47.693','2022-02-07 13:40:47.693','mU37SjVcaYNac3bQfGwUpS','Peerlogic','dentistry_general',NULL,NULL,true);

INSERT INTO public.core_practice (created_at,modified_at,id,"name",industry,created_by_id,modified_by_id,active) VALUES
	 ('2022-02-07 13:40:47.693','2022-02-07 13:40:47.693','Qkrboex9vcKQt5PJfhJ6Tu','Pleasant Dental Care Peoria','dentistry_general',NULL,NULL,true);


INSERT INTO public.core_practice (created_at,modified_at,id,"name",industry,created_by_id,modified_by_id,active) VALUES
	 ('2022-02-07 13:40:47.693','2022-02-07 13:40:47.693','kSbgJAwWQMSY66f5FHhy7z','Gentle','dentistry_general',NULL,NULL,true);
	
	
INSERT INTO public.core_practicetelecom (created_at,modified_at,id,"domain",phone_sms,phone_callback,created_by_id,modified_by_id,practice_id,voip_provider_id) VALUES
	 ('2022-02-07 13:40:47.697','2022-02-07 13:40:47.697','2ur6KFfGvAuWkHKADnmw9o','Peerlogic','','',NULL,NULL,'mU37SjVcaYNac3bQfGwUpS','DDVG3RCVhQ9uLucZYZCWTJ');
	
INSERT INTO public.core_practicetelecom (created_at,modified_at,id,"domain",phone_sms,phone_callback,created_by_id,modified_by_id,practice_id,voip_provider_id) VALUES
	 ('2022-02-07 13:40:47.697','2022-02-07 13:40:47.697','DG7Lb5CarzPG7ec4iwGXDX','pleasantdental-peoria','','',NULL,NULL,'Qkrboex9vcKQt5PJfhJ6Tu','DDVG3RCVhQ9uLucZYZCWTJ');

	
INSERT INTO public.core_practicetelecom (created_at,modified_at,id,"domain",phone_sms,phone_callback,created_by_id,modified_by_id,practice_id,voip_provider_id) VALUES
	 ('2022-02-07 13:40:47.697','2022-02-07 13:40:47.697','29PJVxbFnNxvawuY7x3gNq','Gentle','','',NULL,NULL,'kSbgJAwWQMSY66f5FHhy7z','DDVG3RCVhQ9uLucZYZCWTJ');
	
	
INSERT INTO public.core_voipprovider (created_at,modified_at,id,company_name,integration_type,created_by_id,modified_by_id,active) VALUES
	 ('2022-02-07 00:00:00.000','2022-02-07 00:00:00.000','DDVG3RCVhQ9uLucZYZCWTJ','Peerlogic','netsapiens',NULL,NULL,true);
	 
	
INSERT INTO public.netsapiens_integration_netsapiensapicredentials (created_at,modified_at,id,api_url,client_id,client_secret,username,"password",active,created_by_id,modified_by_id,voip_provider_id) VALUES
	 ('2022-02-01 18:42:37.050','2022-02-01 18:42:37.050','UkoK7kn7J6FEdGAtLBTsr4','https://core1-phx.peerlogic.com/ns-api/','peerlogic-api-dev','36eb09ff537d16b2d7fe8895a77aa292','6000@Peerlogic','ab!!UHA8Y8c4wH',true,null,NULL,'DDVG3RCVhQ9uLucZYZCWTJ');
	 
INSERT INTO public.netsapiens_integration_netsapienscallsubscriptions (created_at,modified_at,id,created_by_id,modified_by_id,active,practice_telecom_id,source_id) VALUES
	 ('2022-01-21 18:53:39.836','2022-02-01 18:51:47.459','YvNjTL9Brrt9gPb2fyXdQi',NULL,NULL,true,'2ur6KFfGvAuWkHKADnmw9o','');

-- CALLS 
INSERT INTO public.calls_call (created_at,modified_at,id,call_start_time,call_end_time,duration_seconds,connect_duration_seconds,progress_time_seconds,call_direction,sip_caller_number,sip_caller_name,sip_callee_number,sip_callee_name,checked_voicemail,went_to_voicemail,call_connection,who_terminated_call,referral_source,caller_type,callee_type,callee_id_id,caller_id_id,created_by_id,modified_by_id,practice_id) VALUES
	 ('2022-02-11 17:16:03.198','2022-02-11 17:16:03.198','DSCJj2V3KAGeVhVow3C9yd','2022-02-11 16:16:22.000','2022-02-11 16:18:54.000','00:01:42'::interval,NULL,NULL,'inbound','+16232519476','PATRICK YOUNG','+16238480100','',false,false,'connected','caller','','non_agent','agent',NULL,NULL,NULL,NULL,'kSbgJAwWQMSY66f5FHhy7z');

INSERT INTO public.calls_callpartial (created_at,modified_at,id,call_id,created_by_id,modified_by_id,time_interaction_ended,time_interaction_started) VALUES
	 ('2022-02-11 17:24:16.288','2022-02-11 17:24:16.288','cJjkUGYEH6A4UQSfs5ZPnm','DSCJj2V3KAGeVhVow3C9yd',NULL,NULL,'2022-02-11 23:17:31.000','2022-02-11 23:16:22.000'),
	 ('2022-02-11 17:24:19.190','2022-02-11 17:24:19.190','N4wu9Khdht8EKHEQd5v6xU','DSCJj2V3KAGeVhVow3C9yd',NULL,NULL,'2022-02-11 23:18:54.000','2022-02-11 23:18:21.000');

INSERT INTO public.calls_callaudiopartial (created_at,modified_at,id,mime_type,status,call_partial_id,created_by_id,modified_by_id) VALUES
	 ('2022-02-11 17:30:26.318','2022-02-11 17:37:12.103','WUNTPU6Zaa4Px2BwkkFYmr','audio/WAV','uploaded','cJjkUGYEH6A4UQSfs5ZPnm',NULL,NULL),
	 ('2022-02-11 17:30:45.042','2022-02-11 17:39:03.332','BVqVRRPoNQLFAW4zoCfGVm','audio/WAV','uploaded','N4wu9Khdht8EKHEQd5v6xU',NULL,NULL);
INSERT INTO public.calls_callaudio (created_at,modified_at,id,mime_type,status,created_by_id,modified_by_id,call_id) VALUES
	 ('2022-02-12 21:49:21.843','2022-02-15 16:00:45.973','6DT24knHY8DhpsdBnMcBr3','audio/WAV','uploaded','ghsmJdDRUHiikyKbA9xS6w','ghsmJdDRUHiikyKbA9xS6w','DSCJj2V3KAGeVhVow3C9yd');
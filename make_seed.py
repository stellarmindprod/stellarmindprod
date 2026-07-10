import csv
import io
from werkzeug.security import generate_password_hash

student_data_raw = """
033de4fe-3f49-4961-b50f-199e5206c371,b240004,$2a$10$KLiEJnuCj2tGhK3q3/Qfp.pBOqVK7QfoJoLUtXWsx6zXSu8.9FmwS,,Battula venkata Niranjan,2025-09-12 21:01:04.917476
0b55bc7e-ddda-47e5-831f-655150bfef7b,b240059,$2a$10$MiUU1J5/N6BeSmAA4DRwgOUOsvRqZUoDbLFlaSWLhNx511yAVy0HO,,Shivanshu kumar,2025-09-12 21:01:04.917476
0e79ce20-1a5c-431a-8d40-b9d4516a7937,b240003,206546,,,2025-09-12 21:01:04.917476
0fc1ec79-5632-4eee-be5f-ff73326967f9,b240033,$2a$10$bvmXdJPFIynrzfx224lDJOx41FfoNBFG2TGnyd1D/NTQSGljtRe76,,Anuska Mandal,2025-09-12 21:01:04.917476
12e16303-e8e1-4d95-bd50-2e14c396cbad,b240008,$2a$10$wb1H5sLI6lKp3WS23iRgz.AvJ53tW9Mf0pS1mIoOV4xZ.fP82rbZS,,Divyangna Puri Goswami,2025-09-12 21:01:04.917476
21fbda89-c8b4-48da-9a5f-ceaf55945fe3,b240011,$2a$10$CWIkrQ.nWNKgJKzoq6NpDuXV1yvNA0u.KdxuNfY6W3fps/MmlgFLe,,Kelbhin Brahma,2025-09-12 21:01:04.917476
2320f3de-864a-4d2f-a361-2353a66420f8,b240053,$2a$10$kPxz84RK0Yz27UOJV8qVQeRZmyYw.uokzXMksoo8Qc.pFQ4lY7JFO,,Nikhil Rai,2025-09-12 21:01:04.917476
23a11cdd-3761-4d32-b436-f417a926fe89,b240039,$2a$10$/mH754DgOr0qY9zjLK9GBOW5OBgUf9.6J2vxm2foyZGsdOE30XAUW,,Banovath balu,2025-09-12 21:01:04.917476
25fe4503-c695-4e5a-85df-c86e78a9631c,b240002,$2a$10$7QduRfMWjF4EKVgd8GmPZOJLqXSGoMEGch29g/lbQ2PxUAAxeRs4O,,Aryan Vasisth,2025-09-12 21:01:04.917476
2b029b68-192a-4e8b-be46-5cdee1bece5d,b240006,$2a$10$mdrjId.mp1ZcAE4vkp731eCfAqePQQUVOKOP.mRTubo.UZ59O/xGW,,Chaitanya Kashyap,2025-09-12 21:01:04.917476
2f734bb4-9836-4cb7-b60c-0095b8832ec4,b240055,$2a$10$wC.7imI0sM5Zn4SkJNHoqeZvQskabj5BjqhMKfz2Q2.lOb8n5yQdq,,Pawan Kumar Limboo,2025-09-12 21:01:04.917476
303b4665-fe65-4a09-8941-4db3820efd90,b240049,$2a$10$QOdSbrtCLpCHk/Fxqa.nsuUTg5dYtmJqQGlToPve4FGlEIzAx9PBq,,Manisha Verma,2025-09-12 21:01:04.917476
32b816a8-b0d1-496a-8e8e-a75fb72d0649,b240019,$2a$10$I1wXsWIAm2as0AK/Q3i2yerTvdD51pJDro0buwQyM9OkqBEdMthgO,,pravesh sharma,2025-09-12 21:01:04.917476
3627caab-2ea7-4656-8dcc-200b48fba415,b240158,$2a$10$IAoHKmxRz1P05AAYPOFEu.ddjAu70gNQljxwobxP2RMIh7Qm011ru,,Sana Tasneem,2025-09-19 13:43:37.734764
3e10e102-46ed-4d19-a58b-1096bce77dbe,b240046,$2a$10$5Cg/zk.kL.WTC.ZHUzamGOJ1qyVUI5URQC5AsxAfh/1kg.azFxHCe,,KURRA ROHITH SAI CHOWDARY,2025-09-12 21:01:04.917476
3ebb4b54-f3b0-43d5-8844-0c63055141e2,b240032,$2a$10$g.9yQJDnF7eB0xW30UhyiesGS8XPJJ8rDVdKPnRknSn9OKiqoYQbS,,Ankit Rawat,2025-09-12 21:01:04.917476
3fa761e0-1a62-4a89-88fd-6d162cb1ac0d,b240016,$2a$10$W3mY1COhu1uoQhNJ8863P..YG0FLLapm1N9HrXWclAGNHigUIunvW,,Nitin Kumar Jha,2025-09-12 21:01:04.917476
47ecdb9c-0c4a-445a-b66d-4526d044dbb2,b240109,$2a$10$sJAXxeFpLy2EFrRmwwS2huebcD0dNTgrmHftXvBBHUqPQQP4iurte,,PRINCE RAJ,2025-09-13 18:44:01.623772
488c1c9d-f009-4925-a350-9cde99abec97,b240026,$2a$10$QIA/XHyyTKlBUx5uRjOJ3.qv4UKz76ELqfEWBqEFtV54hhTC/ioq6,,Subhajeet Das,2025-09-12 21:01:04.917476
4e6518ba-d7a9-45e5-8ae5-551c69c948da,b240086,$2a$10$3W4cc7W2Daupf/JLqVMfp.xyNu0cysPzAZZAzF.eBYN8MzqvmTOtq,,Shandhiya Chhetri,2025-09-20 16:40:17.716734
55d95a11-6d72-49f5-bacb-0670ab881463,b240038,$2a$10$vccAFUUfeljDaiVt3MleDObQtUQaZYM.lZwiOuXBGu895ydiBTL2e,,Ayush Chauhan,2025-09-12 21:01:04.917476
59bb3ff3-4517-4861-9151-d0c1289d0208,b240035,$2a$10$7VkV1hy3mOdgwDFphnqd5OCwNtLRAkwpmLMtcT5bgbV9JSze/cxTK,,Aryan singh,2025-09-12 21:01:04.917476
5c1fccff-0f68-4cf9-8cf8-72c5d8769d58,b240015,$2a$10$h1qGcXOiUQ4vqFSbn1GiIeHm1eJk9Z546gpsehONwAb46Xj9IJzdu,,neeradi Kruthagna,2025-09-12 21:01:04.917476
5e35f65e-154e-494e-a956-a92b54485955,b240005,$2a$10$h/4ZrbZjOjKGxk6t8U9x/O14dzrP14Jgq8d5kTRsiCijRrP.1VeYW,,Bhavya Singhal,2025-09-12 21:01:04.917476
699926e2-b58e-4a10-8b30-370ad47a0f08,b240064,$2a$10$.V/krlEEXFkMQEE.5YzYZOHRL4Y4O18SvCs8PD1Q1C6HDIgSjj07e,,Tarun Kanishk,2025-09-12 21:01:04.917476
6f7c45fd-8bec-4443-ab2f-d21753ce7088,b240007,$2a$10$3DkG3F/A1o4/QguGePUI..Rt6QgSUYFQzrre/c0QaoYCafPuGcWtW,,Darshan chettri,2025-09-12 21:01:04.917476
72a1d50d-40da-4b5e-bfea-06e6ea4b3b62,b240022,$2a$10$exOIxE8DxZD1ZT60hQcy7uSzyK56ozsViqXtfVAZQi22cGh0xkSRm,,Raj Singh,2025-09-12 21:01:04.917476
7462c7e6-2220-47c1-a267-efcee1a2f632,b240063,$2a$10$hsQ70ES7EQR.6lRU9ZRGte2i4hwRRZeZYPOi4OO.PxN4jBw6qJj2.,,Tanmay,2025-09-12 21:01:04.917476
747a41d2-0504-4977-9b34-a398f0bc0d60,b240060,$2a$10$3rNqf3SZh0x9rbqDyGjGB.bDhT90ny50GMwqh.rf9/98C3GDvQGM2,,Sumesh Kumar,2025-09-12 21:01:04.917476
75c6bbad-6310-4f6f-8498-ff5e7b6ee87c,b240028,$2a$10$jAUojw.2lKNSiee2HASgDuneJHe7qBrsOPw51.7y5ZYpUgKXomrQy,,Vishal Prasad,2025-09-12 21:01:04.917476
79e56760-4ca4-45db-8b70-a45fe1dcfcac,b240047,$2a$10$eWYaaTib4GO39nb8te7NkOoq6GUW9RtAjjPoKTV3bKBt3Qp8jksYu,,LavanyaSrivastav,2025-09-12 21:01:04.917476
7b3d7cf8-b57a-47a7-9a50-df4256610b67,b240091,$2a$10$5biBuzLNIcULZRytHDIcjecmDYMmMO/9Wxo1.DWj2wqzVmdZtF4Ie,,Swastika Bauri,2025-09-20 16:40:41.995239
80e41e88-8ecc-4a55-8cfa-f18e9208f946,b240040,$2a$10$nPWdxqjQuwTuXhgKn8xojeRno00p.gu19tEyJUF/0x1Uyh8Qs8L92,,Bhavya kuryawat,2025-09-12 21:01:04.917476
83a326ca-339b-4d5f-a0a6-93f9d9debfba,b240036,$2a$10$ZG.qovtbwFsoKXM1AcCYr.Hq4Zw7A2vK8ZRoZd29qpe2jr3IzW8uG,,Ashish Gupta,2025-09-12 21:01:04.917476
83d674c6-d274-430a-a560-574e4db3c0a2,b240057,$2a$10$FI1j0kDuR08hzJfatDtjD..GCH0.hWYYBqzGsr6JpIF6H6MKAZ1ka,,Rohit Gurung,2025-09-12 21:01:04.917476
8584449f-9148-4ce1-85fd-d36ac4129a29,b240021,423798,,,2025-09-12 21:01:04.917476
8c509efd-92e2-4603-9ac1-98fcb0ba7bdb,b240025,$2a$10$hF4X5F611nsKiVxl46.1QuCYo3NNge/UgbAsJ4MssgHCGdXe7o3BW,,Sriramoju Srujan,2025-09-12 21:01:04.917476
a36f64c1-2a0e-48d0-b574-517c0e7d74fe,b240034,$2a$10$vTRHrrJfu6k1hkXdDiLqwO2yXt3stYJVbRSTEvdv9ws37irtwsvay,,Aryaman Prasad,2025-09-12 21:01:04.917476
a3b974aa-5cef-449e-8f86-f9ba5870fbf7,b240012,$2a$10$HWfPRql4bL1RrUnqvaBfuurc7X5s5aug88EPg5NeaU7cLn7XWY.au,,Keshav bhardwaj,2025-09-12 21:01:04.917476
a499cef2-a220-4c54-adb3-a207a676caf6,b240014,579138,,,2025-09-12 21:01:04.917476
abdec7e5-4bad-4243-8e6e-e58d73d83ac3,b240051,$2a$10$uxZUk127iJZR.mag6uBowO0IwTAf0zpxk3C8ZDpCnF6whDXDW9zIe,,Mohit,2025-09-12 21:01:04.917476
aeb3b216-ebeb-4330-91de-5790bf4db624,b240009,$2a$10$YXTEzC9jjTnp6AhDyZEcwO051vM5xXEtnHpyzVPVql93bs1rsxkZ.,,Janhvi Gupta,2025-09-12 21:01:04.917476
b44aa1c0-714a-443b-870d-c8ebca008aef,b240094,$2a$10$PGc0wQVWpBo3o6NWPyMbCO9V3aVJl0yyCvVmt1C.huxuyHysMGwyy,,Adarsh Yadav,2025-09-13 07:10:54.392778
b912607b-ed40-4c5e-a72d-21b191efe569,b240001,$2a$10$H8X/yVEKNtwCGxjfmJoEX.fkDl7spl3ZNE/yoZrDQHKy8/7X7qkvq,,AARTI KUMARI,2025-09-12 21:01:04.917476
b92c5b75-ed08-4c09-b326-8ee0aebb1871,b240042,$2a$10$vMnIcfLFKc3GhGZGCB2Hu.Eb0Fcnjv1zPktoZtb/NN/J/uW.JPzz.,,Dinesh Saini,2025-09-12 21:01:04.917476
ba9e1e4e-6696-4c8e-9d0f-524aa154ddde,b240030,$2a$10$s2Ky38MB5brhXXe0XUXDguraO1DWyKXNQpz5/N0PRIDBqGOb6scW.,,Aditya,2025-09-12 21:01:04.917476
bd464a32-41cb-48a9-929d-a33860e598e4,b240058,$2a$10$yc9WzMFhfa7h1P4inS5CgOx2ZmtYLK3BqBwCygg3GmLmhq/z67wnG,,Shivangi yadav,2025-09-12 21:01:04.917476
bd77458c-1fe6-48b3-b891-d7b2f4750e0f,b240062,$2a$10$2BDJC9cSLsrZS3ufHcmyOOpgOoIfGudLXaAwA5sn7fmZpVQ01.iWC,,Sumit Singh,2025-09-12 21:01:04.917476
be2fb1d2-4a2b-4fbc-8283-e4f836f759e1,b240050,$2a$10$YmN2Dl1SAzuP3vM2mE5mT.TTbFm6A2CeGeKqdQg5K5DQzyCwVydUK,,Mansi Chaudhary,2025-09-12 21:01:04.917476
c003d62b-0b73-4826-8355-8cd51cd4f679,b240052,$2a$10$vPbaJogwSyLqEwMyda7zx.bl7d8nEk4mdEr9fsUtoqTmbqV3KtVPm,,createyouraccount.1234321,2025-09-12 21:01:04.917476
c1a85782-c7c2-45ad-b316-b911c8da4d4c,b240029,$2a$10$YKf6WB6tGpkr/jvMR1/CseEIWwYa4eBZcQ76.9dKiw4c7hMENyzKS,,Aditya,2025-09-12 21:01:04.917476
c4814856-6757-407a-b0b4-bd08f95611b0,b240112,$2a$10$HGUcuVGZ8iyCMiYlB3o8c.F5QuK3.9HFSdiudjgq8BqGi.hUV2aAG,,Rahul shah,2025-09-13 18:43:26.923451
c7db93b0-1f70-46ce-9919-7a695b3fc719,b240045,$2a$10$GgBoBMhZ4L5D6Ya8AHtaeOVYgb4rUqEcHHaLZiRVgQMgV9C4TC4Be,,Kausal Sharma,2025-09-12 21:01:04.917476
c9e2e68d-fd55-4b2c-b9e0-4efc9cee1204,b240010,$2a$10$hVUFResrCRgq1h3j/ENyFODLjKfnjb7KheGKcE8uhZfR76UDWWvnq,,Jyotish Aaryan,2025-09-12 21:01:04.917476
c9fa0015-fb88-4e88-bf27-dd81acf78851,b240027,$2a$10$NxJFOC9qq.z0MVN8nsPST.kes5WoNtE1i4vzzipscHU7J4oLDpU22,,Suman Raj,2025-09-12 21:01:04.917476
cb433fdd-7a8f-4341-8cb3-55ac5ea8bd3d,b240061,$2a$10$4UZJczqFgFxrFDS.rw506ekaoQyzARKGXNg5SLp/o4k9TvvWQAur6,,Sumit,2025-09-12 21:01:04.917476
d2186e4f-232e-48bf-9611-f085b9d6224d,b240041,$2a$10$XrbJU.KHQqtKzmONKTsfhO39N.tiOC1wfcQbL2HaENu48i1QsOM3W,,Deepanjal Shukla,2025-09-12 21:01:04.917476
d2fc9707-53df-4d8f-9783-3f247ed32e13,b240037,122182,,,2025-09-12 21:01:04.917476
d50d97ba-97c2-4927-b3d6-2d4e7a89deb0,b240044,$2a$10$oYjh30n1PVBq.Od371sFiuLzBeu7xA7ilG2y5KI4d5BvaAqtjxq/i,,Kalle Mahendra,2025-09-12 21:01:04.917476
d76876ae-0f63-480e-b2b3-ad0fd26075a4,b240031,$2a$10$5K5JpsDYct1b0tvSftcCcOY8NZs2Y.EIrCZHUtKz46Qx6apN2bpGS,,ADITYA PRASAD,2025-09-12 21:01:04.917476
d8ecbdcf-e9a6-4ed2-ade3-bfbc7e28d61c,b240043,$2a$10$sMKG6JCDuG9X8OufUOsVLenwdN/hGkUW2kyjCn/CMJKujsfCxB3qK,,Himanshu Kumar,2025-09-12 21:01:04.917476
df52e089-b1e8-43b7-bde2-f61709c4f14b,b240013,$2a$10$6W1Xl.V/Ts8AfbOTTnteQOSgx8gV84bVgIhnziebWl3aHhree4Jsi,,K.T.Sandeep,2025-09-12 21:01:04.917476
e0dc65fd-3881-4434-9f43-95f43a251571,b240023,$2a$10$GriCpldrVlJzSU/HF5Nnke2EriCL2JQnfRTohNXp/KcngTW.12Tlu,,Sabbarapu Karthikeya,2025-09-12 21:01:04.917476
e9140c95-0b57-453d-913b-126dd416223f,b240056,$2a$10$ejz/jCCMHPi80MMPZG0RZOP11KyrhyG85jzVokHwUYhCOGUN1BFI6,,Ravi Kumar Sharma,2025-09-12 21:01:04.917476
ee62a3d3-16f6-4b60-affa-6fdfa26437cc,b240081,$2a$10$FYtnv6CZWSLwoLT/a7hXN.698C.PUXRdn55kTyx2pbWP6we6rA61e,,Rakshit Singh,2025-09-19 08:12:05.026776
f19bbe56-9e55-4a42-926e-0b452b6689db,b240024,$2a$10$ZLtSq1lrvlWKTmGC1z9Oq.8ESMiHf7dWmG5kObd7ZZ2mrgPvzS/FS,,Sanjeev Kumar Gupta,2025-09-12 21:01:04.917476
f1ab1613-70e4-475c-adc1-da9f4567befb,b240048,$2a$10$yoxrDoK4UiWKHvABpkZ7R.mfOAmZA4H9zPIRt9GHDUbbc30KOA/xq,,Leah Sonowal,2025-09-12 21:01:04.917476
f33a602b-5719-422e-b8c1-d5710af01f3c,b240020,$2a$10$6uTl02HI0xjgr3SnZWiGfOun5PvUZveNWtIJBWZ7/qO4wISLKeu3y,,Prem akoskar,2025-09-12 21:01:04.917476
f805be16-731b-4575-a2ad-64e4aee9c237,b240054,$2a$10$20yrDiI4bd2ZF3ICnBXZ2esnNpYRTtoqC2ZplodAvxHzFjFex8uJm,,Nim Deeki Sherpa,2025-09-12 21:01:04.917476
fc42f1e2-ccd5-42f1-b4cb-d977e8ec9078,b240018,$2a$10$YYLNTl7LaoQKf0CdP08aIOt6XhZy5DwsCCBY8oxz4LEBFfB6cDsA2,,Pawan Kumar Singh,2025-09-12 21:01:04.917476
fd15d79f-faf0-4461-a0ac-7823fd634784,b240017,$2a$10$eBWske0FFVZ4EH1kpEv0iO3qIetw5v1XWUfwlKPhcV3Z9ifEw/.r2,,Om kumar,2025-09-12 21:01:04.917476
"""

teacher_data_raw = """
1,teacherrakshit,Rakshit Singh,ROOM218,roomate,superpass,2025-09-10 07:40:08.868949,
3,MSA,Dr. Md. Sarfaraj Alam Ansari,CS13112,COMPUTER NETWORKS,12345,2025-09-16 16:36:53.040102,sarfaraj@nitsikkim.ac.in
7,"PRATYAY SIR ",Dr. Pratyay Kuila,,NULL,12345,2025-09-16 16:40:59.851738,pratyay_kuila@nitsikkim.ac.in
8,SANGRAM SIR,Dr. Sangram Ray,,NULL,12345,2025-09-16 16:41:37.027589,sray.cse@nitsikkim.ac.in
9,bbsinha,Dr. Bam Bahadur Sinha,CS13116,FOUNDATION OF MACHINE LEARNING,$2a$10$uNocq92axwah1CJNQlgxHeeYwh9yuc5BqxA/wHtPzU1AoDUNvYWr.,2025-09-16 16:43:06.719951,bambahadursinha@nitsikkim.ac.in
10,KRISHNA SIR,Dr. Krishna Kumar,,NULL,12345,2025-09-16 16:43:53.09614,krishnakumar@nitsikkim.ac.in
11,pankaj_sir,Dr. Pankaj Kumar Keserwani,CS13114,Object Oriented System Design,$2a$10$K2oUvprDMAL0omktlEMFROp8SOM0Vo4Kddk114scmVgo8lAwRk7ny,2025-09-16 16:45:43.784225,b240005@nitsikkim.ac.in
12,DIKSHA MAM,Dr. Diksha Rangwani,,NULL,12345,2025-09-16 16:46:46.774531,diksharangwani@nitsikkim.ac.in
13,bhavya,bhavya,CS13116,FOUNDATION OF MACHINE LEARNING,$2a$10$q1yoQd5H/zexnkOMDaOcjuWqICFrmz2XowyNSck661NIUp3w/SlSS,2025-09-16 21:18:34.533505,b240005@nitsikkim.ac.in
15,laraib,Laraib Ahmad,CS13111,Data structure and Algorithms,$2a$10$WY8EPA6MQGC2KFYNRE8xMeVELaAu/BdWlXDUpkKgN8qVnToKXXl/C,2025-09-22 18:40:40.686233,singhalbhavya380@gmail.com
16,jayshree_mam,jayshree,CS13113,DIGITAL LOGIC DESIGN,12345,2025-10-08 11:48:04.158676,jayshreechy@gmail.com
17,prashant_sir,prashant,CS13214,SYSTEM DESIGN LABORATORY USING PYTHON,$2a$10$MwR3gJp.JpiJBWVhQDBpseBT8grdarOMsMgtuFRVyhhBgSKohBO4C,2025-10-09 23:00:50.181121,b240005@nitsikkim.ac.in
18,laraib_dsa,laraib ahmed,CS13211,DATA STRUCTURES AND ALGORITHMS LABORATORY,$2a$10$vVDXWLoV.QS.QGLe/R55bu.zjtKb902qxHz92cqj7vNVWInZZPKAK,2025-10-09 23:16:03.399831,b240005@nitsikkim.ac.in
19,dummytestfornewrakshit,newrakshitnewnikhilnewcontainnewthing,,dummy_nohange,$2a$10$qe1xHdQ8CqLUWP1gNgZeJeBWAUGK4PjaEr6OquQ7XStWBlw/hm37q,2025-10-13 17:30:06.03402,b240081@nitsikkim.ac.in
20,Laraib,Laraib Ahmad sir,CS13111,Data Structure and Algorithm,$2a$10$DNissAnK/SCOcKoZnmyXfOaD//sOw8DiRLTvnquKv1SDkh6YHonZG,2025-10-17 16:07:57.417174,laraib@nitsikkim.ac.in
f788e3e1-2b5a-48ee-b91a-209ef26ea3a0,bambahadursinha,$2a$10$bngPtqBr4PsMGFq4Ut502uP/c1PPcsG.ONBhXQfuJGnZpvig5qYnG,CS100,NULL,$2a$10$bngPtqBr4PsMGFq4Ut502uP/c1PPcsG.ONBhXQfuJGnZpvig5qYnG,2025-09-13 07:58:44.817572,bb@nitsikkim.ac.in
"""

def hash_pass(pwd):
    if pwd.startswith('$2a$') or pwd.startswith('scrypt:'):
        return pwd
    return generate_password_hash(pwd)

with open("reset_data.sql", "w") as f:
    f.write("-- SQL Script to truncate existing tables and seed with new requested data\n\n")

    f.write("TRUNCATE TABLE b1 RESTART IDENTITY CASCADE;\n")
    f.write("TRUNCATE TABLE b2 RESTART IDENTITY CASCADE;\n")
    f.write("TRUNCATE TABLE b3 RESTART IDENTITY CASCADE;\n")
    f.write("TRUNCATE TABLE b4 RESTART IDENTITY CASCADE;\n")
    f.write("TRUNCATE TABLE teachers RESTART IDENTITY CASCADE;\n\n")

    f.write("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS subject_code TEXT;\n")
    f.write("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS subject_name TEXT;\n")
    f.write("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS teacher_email TEXT;\n")
    f.write("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();\n\n")
    
    # Process students
    f.write("-- Inserting Students dynamically into `b1` since roll numbers usually start with b24\n")
    student_reader = csv.reader(io.StringIO(student_data_raw.strip()))
    for row in student_reader:
        if not row or len(row) < 6: continue
        uid = row[0].strip()
        roll_no = row[1].strip()
        password = row[2].strip()
        student_name = row[4].strip()
        
        if not student_name:
            student_name = f"Student_{roll_no.upper()}"

        email = f"{roll_no.lower()}@nitsikkim.ac.in"
        hashed = hash_pass(password) if password else hash_pass('12345678')
        
        # We will insert them into b1 for now, or just distribute by batch based on roll: b24=b1, b23=b2
        table_name = "b1"
        if roll_no.lower().startswith('b23'): table_name = "b2"
        elif roll_no.lower().startswith('b22'): table_name = "b3"
        elif roll_no.lower().startswith('b21'): table_name = "b4"
        
        safe_student_name = student_name.replace("'", "''")
        f.write(f"INSERT INTO {table_name} (roll_no, student_name, student_email, student_password, department) VALUES ('{roll_no}', '{safe_student_name}', '{email}', '{hashed}', 'Computer Science');\n")

    f.write("\n-- Inserting Teachers\n")
    teacher_reader = csv.reader(io.StringIO(teacher_data_raw.strip()))
    seen_teacher_emails = set()
    
    for row in teacher_reader:
        if not row or len(row) < 6: continue
        tid = row[0].strip()
        username = row[1].strip().replace("\"", "").replace(" ", "")
        t_name = row[2].strip().replace("\"", "").replace("'", "''")
        subj_code = row[3].strip()
        subj_name = row[4].strip()
        password = row[5].strip()
        created_at = row[6].strip()
        email = row[7].strip() if len(row) > 7 else ""
        
        hashed = hash_pass(password) if password else hash_pass('12345678')

        # Handle duplicate unique emails
        if email and email in seen_teacher_emails:
            base, ext = email.split('@') if '@' in email else (email, '')
            counter = 1
            while f"{base}_{counter}@{ext}" in seen_teacher_emails:
                counter += 1
            email = f"{base}_{counter}@{ext}"
        if email:
            seen_teacher_emails.add(email)

        f.write(f"INSERT INTO teachers (username, teacher_name, department, teacher_password, subject_code, subject_name, teacher_email) VALUES ('{username}', '{t_name}', 'Computer Science', '{hashed}', '{subj_code}', '{subj_name}', '{email}');\n")

    f.write("\n-- Finished Script\n")

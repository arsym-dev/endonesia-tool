import math
import struct

TABLE_OFFSET = 0xA1
LINEBREAK = 0x0A
NAME_VARIABLE = 0x256E
SPECIAL_CHAR_START = '{'
SPECIAL_CHAR_END = '}'

table = [12288,12289,12290,65292,65294,12539,65306,65307,65311,65281,12443,12444,180,65344,168,65342,65507,65343,12541,12542,12445,12446,12291,20189,12293,12294,12295,12540,8213,8208,65295,65340,65374,8741,65372,8230,8229,8216,8217,8220,8221,65288,65289,12308,12309,65339,65341,65371,65373,12296,12297,12298,12299,12300,12301,12302,12303,12304,12305,65291,65293,177,215,247,65309,8800,65308,65310,8806,8807,8734,8756,9794,9792,176,8242,8243,8451,65509,65284,65504,65505,65285,65283,65286,65290,65312,167,9734,9733,9675,9679,9678,9671,9670,9633,9632,9651,9650,9661,9660,8251,12306,8594,8592,8593,8595,12307,0,0,0,0,0,0,0,0,0,0,0,8712,8715,8838,8839,8834,8835,8746,8745,0,0,0,0,0,0,0,0,8743,8744,65506,8658,8660,8704,8707,0,0,0,0,0,0,0,0,0,0,0,8736,8869,8978,8706,8711,8801,8786,8810,8811,8730,8765,8733,8757,8747,8748,0,0,0,0,0,0,0,8491,8240,9839,9837,9834,8224,8225,182,0,0,0,0,9711,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,65296,65297,65298,65299,65300,65301,65302,65303,65304,65305,0,0,0,0,0,0,0,65313,65314,65315,65316,65317,65318,65319,65320,65321,65322,65323,65324,65325,65326,65327,65328,65329,65330,65331,65332,65333,65334,65335,65336,65337,65338,0,0,0,0,0,0,65345,65346,65347,65348,65349,65350,65351,65352,65353,65354,65355,65356,65357,65358,65359,65360,65361,65362,65363,65364,65365,65366,65367,65368,65369,65370,0,0,0,0,12353,12354,12355,12356,12357,12358,12359,12360,12361,12362,12363,12364,12365,12366,12367,12368,12369,12370,12371,12372,12373,12374,12375,12376,12377,12378,12379,12380,12381,12382,12383,12384,12385,12386,12387,12388,12389,12390,12391,12392,12393,12394,12395,12396,12397,12398,12399,12400,12401,12402,12403,12404,12405,12406,12407,12408,12409,12410,12411,12412,12413,12414,12415,12416,12417,12418,12419,12420,12421,12422,12423,12424,12425,12426,12427,12428,12429,12430,12431,12432,12433,12434,12435,0,0,0,0,0,0,0,0,0,0,0,12449,12450,12451,12452,12453,12454,12455,12456,12457,12458,12459,12460,12461,12462,12463,12464,12465,12466,12467,12468,12469,12470,12471,12472,12473,12474,12475,12476,12477,12478,12479,12480,12481,12482,12483,12484,12485,12486,12487,12488,12489,12490,12491,12492,12493,12494,12495,12496,12497,12498,12499,12500,12501,12502,12503,12504,12505,12506,12507,12508,12509,12510,12511,12512,12513,12514,12515,12516,12517,12518,12519,12520,12521,12522,12523,12524,12525,12526,12527,12528,12529,12530,12531,12532,12533,12534,0,0,0,0,0,0,0,0,913,914,915,916,917,918,919,920,921,922,923,924,925,926,927,928,929,931,932,933,934,935,936,937,0,0,0,0,0,0,0,0,945,946,947,948,949,950,951,952,953,954,955,956,957,958,959,960,961,963,964,965,966,967,968,969,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1040,1041,1042,1043,1044,1045,1025,1046,1047,1048,1049,1050,1051,1052,1053,1054,1055,1056,1057,1058,1059,1060,1061,1062,1063,1064,1065,1066,1067,1068,1069,1070,1071,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1072,1073,1074,1075,1076,1077,1105,1078,1079,1080,1081,1082,1083,1084,1085,1086,1087,1088,1089,1090,1091,1092,1093,1094,1095,1096,1097,1098,1099,1100,1101,1102,1103,0,0,0,0,0,0,0,0,0,0,0,0,0,9472,9474,9484,9488,9496,9492,9500,9516,9508,9524,9532,9473,9475,9487,9491,9499,9495,9507,9523,9515,9531,9547,9504,9519,9512,9527,9535,9501,9520,9509,9528,9538,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9312,9313,9314,9315,9316,9317,9318,9319,9320,9321,9322,9323,9324,9325,9326,9327,9328,9329,9330,9331,8544,8545,8546,8547,8548,8549,8550,8551,8552,8553,0,13129,13076,13090,13133,13080,13095,13059,13110,13137,13143,13069,13094,13091,13099,13130,13115,13212,13213,13214,13198,13199,13252,13217,0,0,0,0,0,0,0,0,13179,12317,12319,8470,13261,8481,12964,12965,12966,12967,12968,12849,12850,12857,13182,13181,13180,8786,8801,8747,8750,8721,8730,8869,8736,8735,8895,8757,8745,8746,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,20124,21782,23043,38463,21696,24859,25384,23030,36898,33909,33564,31312,24746,25569,28197,26093,33894,33446,39925,26771,22311,26017,25201,23451,22992,34427,39156,32098,32190,39822,25110,31903,34999,23433,24245,25353,26263,26696,38343,38797,26447,20197,20234,20301,20381,20553,22258,22839,22996,23041,23561,24799,24847,24944,26131,26885,28858,30031,30064,31227,32173,32239,32963,33806,34915,35586,36949,36986,21307,20117,20133,22495,32946,37057,30959,19968,22769,28322,36920,31282,33576,33419,39983,20801,21360,21693,21729,22240,23035,24341,39154,28139,32996,34093,38498,38512,38560,38907,21515,21491,23431,28879,32701,36802,38632,21359,40284,31418,19985,30867,33276,28198,22040,21764,27421,34074,39995,23013,21417,28006,29916,38287,22082,20113,36939,38642,33615,39180,21473,21942,23344,24433,26144,26355,26628,27704,27891,27945,29787,30408,31310,38964,33521,34907,35424,37613,28082,30123,30410,39365,24742,35585,36234,38322,27022,21421,20870,22290,22576,22852,23476,24310,24616,25513,25588,27839,28436,28814,28948,29017,29141,29503,32257,33398,33489,34199,36960,37467,40219,22633,26044,27738,29989,20985,22830,22885,24448,24540,25276,26106,27178,27431,27572,29579,32705,35158,40236,40206,40644,23713,27798,33659,20740,23627,25014,33222,26742,29281,20057,20474,21368,24681,28201,31311,38899,19979,21270,20206,20309,20285,20385,20339,21152,21487,22025,22799,23233,23478,23521,31185,26247,26524,26550,27468,27827,28779,29634,31117,31166,31292,31623,33457,33499,33540,33655,33775,33747,34662,35506,22057,36008,36838,36942,38686,34442,20420,23784,25105,29273,30011,33253,33469,34558,36032,38597,39187,39381,20171,20250,35299,22238,22602,22730,24315,24555,24618,24724,24674,25040,25106,25296,25913,39745,26214,26800,28023,28784,30028,30342,32117,33445,34809,38283,38542,35997,20977,21182,22806,21683,23475,23830,24936,27010,28079,30861,33995,34903,35442,37799,39608,28012,39336,34521,22435,26623,34510,37390,21123,22151,21508,24275,25313,25785,26684,26680,27579,29554,30906,31339,35226,35282,36203,36611,37101,38307,38548,38761,23398,23731,27005,38989,38990,25499,31520,27179,27263,26806,39949,28511,21106,21917,24688,25324,27963,28167,28369,33883,35088,36676,19988,39993,21494,26907,27194,38788,26666,20828,31427,33970,37340,37772,22107,40232,26658,33541,33841,31909,21000,33477,29926,20094,20355,20896,23506,21002,21208,21223,24059,21914,22570,23014,23436,23448,23515,24178,24185,24739,24863,24931,25022,25563,25954,26577,26707,26874,27454,27475,27735,28450,28567,28485,29872,29976,30435,30475,31487,31649,31777,32233,32566,32752,32925,33382,33694,35251,35532,36011,36996,37969,38291,38289,38306,38501,38867,39208,33304,20024,21547,23736,24012,29609,30284,30524,23721,32747,36107,38593,38929,38996,39000,20225,20238,21361,21916,22120,22522,22855,23305,23492,23696,24076,24190,24524,25582,26426,26071,26082,26399,26827,26820,27231,24112,27589,27671,27773,30079,31048,23395,31232,32000,24509,35215,35352,36020,36215,36556,36637,39138,39438,39740,20096,20605,20736,22931,23452,25135,25216,25836,27450,29344,30097,31047,32681,34811,35516,35696,25516,33738,38816,21513,21507,21931,26708,27224,35440,30759,26485,40653,21364,23458,33050,34384,36870,19992,20037,20167,20241,21450,21560,23470,24339,24613,25937,26429,27714,27762,27875,28792,29699,31350,31406,31496,32026,31998,32102,26087,29275,21435,23621,24040,25298,25312,25369,28192,34394,35377,36317,37624,28417,31142,39770,20136,20139,20140,20379,20384,20689,20807,31478,20849,20982,21332,21281,21375,21483,21932,22659,23777,24375,24394,24623,24656,24685,25375,25945,27211,27841,29378,29421,30703,33016,33029,33288,34126,37111,37857,38911,39255,39514,20208,20957,23597,26241,26989,23616,26354,26997,29577,26704,31873,20677,21220,22343,24062,37670,26020,27427,27453,29748,31105,31165,31563,32202,33465,33740,34943,35167,35641,36817,37329,21535,37504,20061,20534,21477,21306,29399,29590,30697,33510,36527,39366,39368,39378,20855,24858,34398,21936,31354,20598,23507,36935,38533,20018,27355,37351,23633,23624,25496,31391,27795,38772,36705,31402,29066,38536,31874,26647,32368,26705,37740,21234,21531,34219,35347,32676,36557,37089,21350,34952,31041,20418,20670,21009,20804,21843,22317,29674,22411,22865,24418,24452,24693,24950,24935,25001,25522,25658,25964,26223,26690,28179,30054,31293,31995,32076,32153,32331,32619,33550,33610,34509,35336,35427,35686,36605,38938,40335,33464,36814,39912,21127,25119,25731,28608,38553,26689,20625,27424,27770,28500,31348,32080,34880,35363,26376,20214,20537,20518,20581,20860,21048,21091,21927,22287,22533,23244,24314,25010,25080,25331,25458,26908,27177,29309,29356,29486,30740,30831,32121,30476,32937,35211,35609,36066,36562,36963,37749,38522,38997,39443,40568,20803,21407,21427,24187,24358,28187,28304,29572,29694,32067,33335,35328,35578,38480,20046,20491,21476,21628,22266,22993,23396,24049,24235,24359,25144,25925,26543,28246,29392,31946,34996,32929,32993,33776,34382,35463,36328,37431,38599,39015,40723,20116,20114,20237,21320,21577,21566,23087,24460,24481,24735,26791,27278,29786,30849,35486,35492,35703,37264,20062,39881,20132,20348,20399,20505,20502,20809,20844,21151,21177,21246,21402,21475,21521,21518,21897,22353,22434,22909,23380,23389,23439,24037,24039,24055,24184,24195,24218,24247,24344,24658,24908,25239,25304,25511,25915,26114,26179,26356,26477,26657,26775,27083,27743,27946,28009,28207,28317,30002,30343,30828,31295,31968,32005,32024,32094,32177,32789,32771,32943,32945,33108,33167,33322,33618,34892,34913,35611,36002,36092,37066,37237,37489,30783,37628,38308,38477,38917,39321,39640,40251,21083,21163,21495,21512,22741,25335,28640,35946,36703,40633,20811,21051,21578,22269,31296,37239,40288,40658,29508,28425,33136,29969,24573,24794,39592,29403,36796,27492,38915,20170,22256,22372,22718,23130,24680,25031,26127,26118,26681,26801,28151,30165,32058,33390,39746,20123,20304,21449,21766,23919,24038,24046,26619,27801,29811,30722,35408,37782,35039,22352,24231,25387,20661,20652,20877,26368,21705,22622,22971,23472,24425,25165,25505,26685,27507,28168,28797,37319,29312,30741,30758,31085,25998,32048,33756,35009,36617,38555,21092,22312,26448,32618,36001,20916,22338,38442,22586,27018,32948,21682,23822,22524,30869,40442,20316,21066,21643,25662,26152,26388,26613,31364,31574,32034,37679,26716,39853,31545,21273,20874,21047,23519,25334,25774,25830,26413,27578,34217,38609,30352,39894,25420,37638,39851,30399,26194,19977,20632,21442,23665,24808,25746,25955,26719,29158,29642,29987,31639,32386,34453,35715,36059,37240,39184,26028,26283,27531,20181,20180,20282,20351,21050,21496,21490,21987,22235,22763,22987,22985,23039,23376,23629,24066,24107,24535,24605,25351,25903,23388,26031,26045,26088,26525,27490,27515,27663,29509,31049,31169,31992,32025,32043,32930,33026,33267,35222,35422,35433,35430,35468,35566,36039,36060,38604,39164,27503,20107,20284,20365,20816,23383,23546,24904,25345,26178,27425,28363,27835,29246,29885,30164,30913,31034,32780,32819,33258,33940,36766,27728,40575,24335,35672,40235,31482,36600,23437,38635,19971,21489,22519,22833,23241,23460,24713,28287,28422,30142,36074,23455,34048,31712,20594,26612,33437,23649,34122,32286,33294,20889,23556,25448,36198,26012,29038,31038,32023,32773,35613,36554,36974,34503,37034,20511,21242,23610,26451,28796,29237,37196,37320,37675,33509,23490,24369,24825,20027,21462,23432,25163,26417,27530,29417,29664,31278,33131,36259,37202,39318,20754,21463,21610,23551,25480,27193,32172,38656,22234,21454,21608,23447,23601,24030,20462,24833,25342,27954,31168,31179,32066,32333,32722,33261,33311,33936,34886,35186,35728,36468,36655,36913,37195,37228,38598,37276,20160,20303,20805,21313,24467,25102,26580,27713,28171,29539,32294,37325,37507,21460,22809,23487,28113,31069,32302,31899,22654,29087,20986,34899,36848,20426,23803,26149,30636,31459,33308,39423,20934,24490,26092,26991,27529,28147,28310,28516,30462,32020,24033,36981,37255,38918,20966,21021,25152,26257,26329,28186,24246,32210,32626,26360,34223,34295,35576,21161,21465,22899,24207,24464,24661,37604,38500,20663,20767,21213,21280,21319,21484,21736,21830,21809,22039,22888,22974,23100,23477,23558,23567,23569,23578,24196,24202,24288,24432,25215,25220,25307,25484,25463,26119,26124,26157,26230,26494,26786,27167,27189,27836,28040,28169,28248,28988,28966,29031,30151,30465,30813,30977,31077,31216,31456,31505,31911,32057,32918,33750,33931,34121,34909,35059,35359,35388,35412,35443,35937,36062,37284,37478,37758,37912,38556,38808,19978,19976,19998,20055,20887,21104,22478,22580,22732,23330,24120,24773,25854,26465,26454,27972,29366,30067,31331,33976,35698,37304,37664,22065,22516,39166,25325,26893,27542,29165,32340,32887,33394,35302,39135,34645,36785,23611,20280,20449,20405,21767,23072,23517,23529,24515,24910,25391,26032,26187,26862,27035,28024,28145,30003,30137,30495,31070,31206,32051,33251,33455,34218,35242,35386,36523,36763,36914,37341,38663,20154,20161,20995,22645,22764,23563,29978,23613,33102,35338,36805,38499,38765,31525,35535,38920,37218,22259,21416,36887,21561,22402,24101,25512,27700,28810,30561,31883,32736,34928,36930,37204,37648,37656,38543,29790,39620,23815,23913,25968,26530,36264,38619,25454,26441,26905,33733,38935,38592,35070,28548,25722,23544,19990,28716,30045,26159,20932,21046,21218,22995,24449,24615,25104,25919,25972,26143,26228,26866,26646,27491,28165,29298,29983,30427,31934,32854,22768,35069,35199,35488,35475,35531,36893,37266,38738,38745,25993,31246,33030,38587,24109,24796,25114,26021,26132,26512,30707,31309,31821,32318,33034,36012,36196,36321,36447,30889,20999,25305,25509,25666,25240,35373,31363,31680,35500,38634,32118,33292,34633,20185,20808,21315,21344,23459,23554,23574,24029,25126,25159,25776,26643,26676,27849,27973,27927,26579,28508,29006,29053,26059,31359,31661,32218,32330,32680,33146,33307,33337,34214,35438,36046,36341,36984,36983,37549,37521,38275,39854,21069,21892,28472,28982,20840,31109,32341,33203,31950,22092,22609,23720,25514,26366,26365,26970,29401,30095,30094,30990,31062,31199,31895,32032,32068,34311,35380,38459,36961,40736,20711,21109,21452,21474,20489,21930,22766,22863,29245,23435,23652,21277,24803,24819,25436,25475,25407,25531,25805,26089,26361,24035,27085,27133,28437,29157,20105,30185,30456,31379,31967,32207,32156,32865,33609,33624,33900,33980,34299,35013,36208,36865,36973,37783,38684,39442,20687,22679,24974,33235,34101,36104,36896,20419,20596,21063,21363,24687,25417,26463,28204,36275,36895,20439,23646,36042,26063,32154,21330,34966,20854,25539,23384,23403,23562,25613,26449,36956,20182,22810,22826,27760,35409,21822,22549,22949,24816,25171,26561,33333,26965,38464,39364,39464,20307,22534,23550,32784,23729,24111,24453,24608,24907,25140,26367,27888,28382,32974,33151,33492,34955,36024,36864,36910,38538,40667,39899,20195,21488,22823,31532,37261,38988,40441,28381,28711,21331,21828,23429,25176,25246,25299,27810,28655,29730,35351,37944,28609,35582,33592,20967,34552,21482,21481,20294,36948,36784,22890,33073,24061,31466,36799,26842,35895,29432,40008,27197,35504,20025,21336,22022,22374,25285,25506,26086,27470,28129,28251,28845,30701,31471,31658,32187,32829,32966,34507,35477,37723,22243,22727,24382,26029,26262,27264,27573,30007,35527,20516,30693,22320,24347,24677,26234,27744,30196,31258,32622,33268,34584,36933,39347,31689,30044,31481,31569,33988,36880,31209,31378,33590,23265,30528,20013,20210,23449,24544,25277,26172,26609,27880,34411,34935,35387,37198,37619,39376,27159,28710,29482,33511,33879,36015,19969,20806,20939,21899,23541,24086,24115,24193,24340,24373,24427,24500,25074,25361,26274,26397,28526,29266,30010,30522,32884,33081,33144,34678,35519,35548,36229,36339,37530,38263,38914,40165,21189,25431,30452,26389,27784,29645,36035,37806,38515,27941,22684,26894,27084,36861,37786,30171,36890,22618,26626,25524,27131,20291,28460,26584,36795,34086,32180,37716,26943,28528,22378,22775,23340,32044,29226,21514,37347,40372,20141,20302,20572,20597,21059,35998,21576,22564,23450,24093,24213,24237,24311,24351,24716,25269,25402,25552,26799,27712,30855,31118,31243,32224,33351,35330,35558,36420,36883,37048,37165,37336,40718,27877,25688,25826,25973,28404,30340,31515,36969,37841,28346,21746,24505,25764,36685,36845,37444,20856,22635,22825,23637,24215,28155,32399,29980,36028,36578,39003,28857,20253,27583,28593,30000,38651,20814,21520,22581,22615,22956,23648,24466,26007,26460,28193,30331,33759,36077,36884,37117,37709,30757,30778,21162,24230,22303,22900,24594,20498,20826,20908,20941,20992,21776,22612,22616,22871,23445,23798,23947,24764,25237,25645,26481,26691,26812,26847,30423,28120,28271,28059,28783,29128,24403,30168,31095,31561,31572,31570,31958,32113,21040,33891,34153,34276,35342,35588,35910,36367,36867,36879,37913,38518,38957,39472,38360,20685,21205,21516,22530,23566,24999,25758,27934,30643,31461,33012,33796,36947,37509,23776,40199,21311,24471,24499,28060,29305,30563,31167,31716,27602,29420,35501,26627,27233,20984,31361,26932,23626,40182,33515,23493,37193,28702,22136,23663,24775,25958,27788,35930,36929,38931,21585,26311,37389,22856,37027,20869,20045,20970,34201,35598,28760,25466,37707,26978,39348,32260,30071,21335,26976,36575,38627,27741,20108,23612,24336,36841,21250,36049,32905,34425,24319,26085,20083,20837,22914,23615,38894,20219,22922,24525,35469,28641,31152,31074,23527,33905,29483,29105,24180,24565,25467,25754,29123,31896,20035,24316,20043,22492,22178,24745,28611,32013,33021,33075,33215,36786,35223,34468,24052,25226,25773,35207,26487,27874,27966,29750,30772,23110,32629,33453,39340,20467,24259,25309,25490,25943,26479,30403,29260,32972,32954,36649,37197,20493,22521,23186,26757,26995,29028,29437,36023,22770,36064,38506,36889,34687,31204,30695,33833,20271,21093,21338,25293,26575,27850,30333,31636,31893,33334,34180,36843,26333,28448,29190,32283,33707,39361,40614,20989,31665,30834,31672,32903,31560,27368,24161,32908,30033,30048,20843,37474,28300,30330,37271,39658,20240,32624,25244,31567,38309,40169,22138,22617,34532,38588,20276,21028,21322,21453,21467,24070,25644,26001,26495,27710,27726,29256,29359,29677,30036,32321,33324,34281,36009,31684,37318,29033,38930,39151,25405,26217,30058,30436,30928,34115,34542,21290,21329,21542,22915,24199,24444,24754,25161,25209,25259,26000,27604,27852,30130,30382,30865,31192,32203,32631,32933,34987,35513,36027,36991,38750,39131,27147,31800,20633,23614,24494,26503,27608,29749,30473,32654,40763,26570,31255,21305,30091,39661,24422,33181,33777,32920,24380,24517,30050,31558,36924,26727,23019,23195,32016,30334,35628,20469,24426,27161,27703,28418,29922,31080,34920,35413,35961,24287,25551,30149,31186,33495,37672,37618,33948,34541,39981,21697,24428,25996,27996,28693,36007,36051,38971,25935,29942,19981,20184,22496,22827,23142,23500,20904,24067,24220,24598,25206,25975,26023,26222,28014,29238,31526,33104,33178,33433,35676,36000,36070,36212,38428,38468,20398,25771,27494,33310,33889,34154,37096,23553,26963,39080,33914,34135,20239,21103,24489,24133,26381,31119,33145,35079,35206,28149,24343,25173,27832,20175,29289,39826,20998,21563,22132,22707,24996,25198,28954,22894,31881,31966,32027,38640,25991,32862,19993,20341,20853,22592,24163,24179,24330,26564,20006,34109,38281,38491,31859,38913,20731,22721,30294,30887,21029,30629,34065,31622,20559,22793,29255,31687,32232,36794,36820,36941,20415,21193,23081,24321,38829,20445,33303,37610,22275,25429,27497,29995,35036,36628,31298,21215,22675,24917,25098,26286,27597,31807,33769,20515,20472,21253,21574,22577,22857,23453,23792,23791,23849,24214,25265,25447,25918,26041,26379,27861,27873,28921,30770,32299,32990,33459,33804,34028,34562,35090,35370,35914,37030,37586,39165,40179,40300,20047,20129,20621,21078,22346,22952,24125,24536,24537,25151,26292,26395,26576,26834,20882,32033,32938,33192,35584,35980,36031,37502,38450,21536,38956,21271,20693,21340,22696,25778,26420,29287,30566,31302,37350,21187,27809,27526,22528,24140,22868,26412,32763,20961,30406,25705,30952,39764,40635,22475,22969,26151,26522,27598,21737,27097,24149,33180,26517,39850,26622,40018,26717,20134,20451,21448,25273,26411,27819,36804,20397,32365,40639,19975,24930,28288,28459,34067,21619,26410,39749,24051,31637,23724,23494,34588,28234,34001,31252,33032,22937,31885,27665,30496,21209,22818,28961,29279,30683,38695,40289,26891,23167,23064,20901,21517,21629,26126,30431,36855,37528,40180,23018,29277,28357,20813,26825,32191,32236,38754,40634,25720,27169,33538,22916,23391,27611,29467,30450,32178,32791,33945,20786,26408,40665,30446,26466,21247,39173,23588,25147,31870,36016,21839,24758,32011,38272,21249,20063,20918,22812,29242,32822,37326,24357,30690,21380,24441,32004,34220,35379,36493,38742,26611,34222,37971,24841,24840,27833,30290,35565,36664,21807,20305,20778,21191,21451,23461,24189,24736,24962,25558,26377,26586,28263,28044,29494,29495,30001,31056,35029,35480,36938,37009,37109,38596,34701,22805,20104,20313,19982,35465,36671,38928,20653,24188,22934,23481,24248,25562,25594,25793,26332,26954,27096,27915,28342,29076,29992,31407,32650,32768,33865,33993,35201,35617,36362,36965,38525,39178,24958,25233,27442,27779,28020,32716,32764,28096,32645,34746,35064,26469,33713,38972,38647,27931,32097,33853,37226,20081,21365,23888,27396,28651,34253,34349,35239,21033,21519,23653,26446,26792,29702,29827,30178,35023,35041,37324,38626,38520,24459,29575,31435,33870,25504,30053,21129,27969,28316,29705,30041,30827,31890,38534,31452,40845,20406,24942,26053,34396,20102,20142,20698,20001,20940,23534,26009,26753,28092,29471,30274,30637,31260,31975,33391,35538,36988,37327,38517,38936,21147,32209,20523,21400,26519,28107,29136,29747,33256,36650,38563,40023,40607,29792,22593,28057,32047,39006,20196,20278,20363,20919,21169,23994,24604,29618,31036,33491,37428,38583,38646,38666,40599,40802,26278,27508,21015,21155,28872,35010,24265,24651,24976,28451,29001,31806,32244,32879,34030,36899,37676,21570,39791,27347,28809,36034,36335,38706,21172,23105,24266,24324,26391,27004,27028,28010,28431,29282,29436,31725,32769,32894,34635,37070,20845,40595,31108,32907,37682,35542,20525,21644,35441,27498,36036,33031,24785,26528,40434,20121,20120,39952,35435,34241,34152,26880,28286,30871,33109]

ascii2eucjptbl = {
    ' ': bytearray([0xa1, 0xa1]),
    ',': bytearray([0xa1, 0xa4]),
    '.': bytearray([0xa1, 0xa5]),
    ':': bytearray([0xa1, 0xa7]),
    ';': bytearray([0xa1, 0xa8]),
    '?': bytearray([0xa1, 0xa9]),
    '!': bytearray([0xa1, 0xaa]),
    '`': bytearray([0xa1, 0xae]),

    '^': bytearray([0xa1, 0xb0]),
    '_': bytearray([0xa1, 0xb2]),
    '/': bytearray([0xa1, 0xbf]),

    '\\': bytearray([0xa1, 0xc0]),
    '~': bytearray([0xa1, 0xc1]),
    '|': bytearray([0xa1, 0xc3]),
    "'": bytearray([0xa1, 0xc7]),
    '"': bytearray([0xa1, 0xc9]),
    '(': bytearray([0xa1, 0xca]),
    ')': bytearray([0xa1, 0xcb]),
    '[': bytearray([0xa1, 0xce]),
    ']': bytearray([0xa1, 0xcf]),

    '{': bytearray([0xa1, 0xd0]),
    '}': bytearray([0xa1, 0xd1]),

    '+': bytearray([0xa1, 0xdc]),
    '-': bytearray([0xa1, 0xdd]),
    
    '=': bytearray([0xa1, 0xe1]),
    '<': bytearray([0xa1, 0xe3]),
    '>': bytearray([0xa1, 0xe4]),
    
    '$': bytearray([0xa1, 0xf0]),
    '%': bytearray([0xa1, 0xf3]),
    '#': bytearray([0xa1, 0xf4]),
    '&': bytearray([0xa1, 0xf5]),
    '*': bytearray([0xa1, 0xf6]),
    '@': bytearray([0xa1, 0xf7]),
}

def convertToString(index):
    upper_byte = index >> 8
    lower_byte = index % 0x100

    ## Newline
    if upper_byte == 0:
        if lower_byte == 0:
            return False
        
        if lower_byte == LINEBREAK:
            return "\\n"

        if lower_byte < 0x20:
            return f'{SPECIAL_CHAR_START}{lower_byte:02X}{SPECIAL_CHAR_END}'
        
        ## ASCII Characters
        return chr(lower_byte)
    
    if index >= 0xA1A1:
        return char((upper_byte - TABLE_OFFSET) * 94 + (lower_byte - TABLE_OFFSET))
    else:
        return f'{SPECIAL_CHAR_START}{index:04X}{SPECIAL_CHAR_END}'

def convertToIndex(string):
    index = ord(string)
    if index in table:
        return table.index(index)
    return -1

def convertToHex(string):
    index = convertToIndex(string)
    if index >= 0:
        lead = math.floor(index / 94) + TABLE_OFFSET
        bite = index % 94 + TABLE_OFFSET
        return (lead << 8) + bite
    return ''

def decode(data):
    text = ''
    while True:
        b = struct.unpack('B', data.read(1))[0]

        ## ASCII text
        if b <= 0x7F:
            result = convertToString(b)
        
        ## Japanese text
        else:
            data.seek(-1, 1)
            char = struct.unpack('>H', data.read(2))[0]
            result = convertToString(char)
        
        if result == False:
            break

        text += result
    return text

def stringToHex(string, transform_ascii=False):
    ## Convert ascii characters to their EUC_JP equivalent
    ## The game does not properly handle one-byte characters
    ## hence the need for this hack

    rv = b""

    size = len(string)
    i = 0
    while i < size:
        ## Process things of the form {00} or {0000}
        if string[i] == SPECIAL_CHAR_START:
            for x in [2, 4]:
                if string[i+x+1] != SPECIAL_CHAR_END:
                    continue

                if x == 2:
                    format = "B"
                else:
                    format = ">H"

                rv += struct.pack(format, int(string[i+1:i+x+1], 16))
                i += x + 2
                break
            continue
        
        ## Process new lines
        elif string[i:i+2] == "\\n":
            rv += struct.pack("B", LINEBREAK)
            i += 2
            continue
        
        ## Process ASCII characters
        char = string[i]
        i += 1

        if transform_ascii:
            if char>='0' and char<='9':
                rv += bytearray([0xa3, 0xB0+int(char)])
                continue

            if char>='A' and char<='Z':
                rv += bytearray([0xa3, 0xC1+ord(char)-ord('A')])
                continue

            if char>='a' and char<='z':
                rv += bytearray([0xa3, 0xE1+ord(char)-ord('a')])
                continue

            if char in ascii2eucjptbl:
                rv += ascii2eucjptbl[char]
                continue
        
        ## Process ASCII characters as-is
        if ord(char) <= 0x7F:
            rv += struct.pack("B", ord(char))
            continue
        
        ## Process japanese characters
        rv += struct.pack(">H", convertToHex(char))
    
    return rv
    # return rv.decode("eucjp") #jis208

def validate(index):
    lead = index >> 8
    bite = index % 0x100
    return index >= 0xA1A1 and (lead - TABLE_OFFSET) * 94 + (bite - TABLE_OFFSET) < len(table)

def char(index):
    return chr(table[index]) if index < len(table) else chr(0)
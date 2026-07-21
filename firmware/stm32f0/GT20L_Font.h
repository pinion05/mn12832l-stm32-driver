#ifndef _GT20L_FONT_H_  
#define _GT20L_FONT_H_  
                                
#include "stm32f0xx_hal.h"
#include "main.h"

extern uint8_t data[4][128];

/*
芯片说明：
GT20L16S1Y 标准汉字字库芯片
GB2312 字符集（6763 汉字）：15x16 点阵
ASCII 符集（6 套）：5x7~8x16 点阵
时钟最大30MHz @3.3V，工作电压2.2-3.6V，8ma
引脚： 1 SCK ；2 GND；3 CS；4 VCC；5 SO；6 SI；

15x16 GB2312汉字
8x16点国标扩展字符
5x7点ASCII字符
7x8点ASCII字符
8x16点ASCII字符
8x16点ASCII粗体字符
16点ASCII不等宽字符
16点ASCII不等宽白正字符


15X16 点汉字的信息需要32 个字节（BYTE 0 – BYTE 31）来表示。
5X7 点ASCII 的信息需要8 个字节（BYTE 0 – BYTE7）来表示
8X16 点字符信息需要16 个字节（BYTE 0 – BYTE15）来表示。
16 点阵不等宽字符的信息需要34 个字节（BYTE 0 – BYTE33）来表示

由于字符是不等宽的，因此在存储格式中 BYTE0~ BYTE1 存放点阵宽度数据，BYTE2-33 存放竖置
横排点阵数据



GB2312标准共收录6763个汉字，其中一级汉字3755个，二级汉字3008个；同时，GB 2312收录了包括拉丁字母、希腊字母、日文平假名及片假名字母、俄语西里尔字母在内的682个全角字符。整个字符集分成94个区，每区有94个位。 
?GB2312，又称为GB0，由中国国家标准总局发布，1981年5月1日实施
?GB2312标准共收录6763个汉字，其中一级汉字3755个，二级汉字3008个
?GB2312是一种区位码。分为94个区(01-94)，每区94个字符(01-94)
?01-09区为特殊符号
?10-15区没有编码
?16-55区为一级汉字，按拼音排序，共3755个
?56-87区为二级汉字，按部首／笔画排序，共3008个
?88-94区没有编码
?GB2312只是编码表，在计算机中通常都是用"EUC-CN"表示法，即在每个区位加上0xA0来表示。区和位分别占用一个字节。


// 中文测试啊， 如：啊对应b0a1
[0]	0xd6
[1]	0xd0
[2]	0xce
[3]	0xc4
[4]	0xb2
[5]	0xe2
[6]	0xca
[7]	0xd4
[8]	0xb0
[9]	0xa1
*/








    
// 将字体30字节置入显存data
// x:0-127, y: 0-32
void  PutFont15x16ToBuff(uint8_t x, uint8_t y, uint8_t* fontHZ);
void  PutFont8x16ToBuff(uint8_t x, uint8_t y, uint8_t* fontHZ);
void  PutFont7x8ToBuff(uint8_t x, uint8_t y, uint8_t* font);
void  PutFont5x7ToBuff(uint8_t x, uint8_t y, uint8_t* font);

#endif  
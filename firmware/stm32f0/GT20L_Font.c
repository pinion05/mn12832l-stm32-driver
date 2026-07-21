#include "GT20L_Font.h"  



  


    
// 将字体30字节置入显存data
// x:0-127, y: 0-32
void  PutFont15x16ToBuff(uint8_t x, uint8_t y, uint8_t* fontHZ)
{
    // y: 1-7 需要移位存到B0，B1，B2三个
    // y: 9-15,需要移位存到B1，B2，B3
    // y：0或者16，直接存B0、B1或者B2、B3
    // y>16，存不下，是否需要循环存放？超出的部分，移位存入B0 大于24时还要存入B1
    uint8_t brow = y;
    
    uint8_t offset;
    
    // 假设目标位置为（0，2）-（0,18），B0计算= 2/8 = 0;
    uint8_t beginBrow = y /8;
    uint8_t B0, B1, B2;   // 字库新的位置。B0对应 data[beginBrow][x], B1=data[beginBrow+1][0], B2=data[beginBrow+2][0];
    
    offset = y % 8;
    if(offset)   // 非整数行时，移位
    {
        for (int i = 0; i < 30; i+=2)
        {                
            if(x>127)  
                continue;
            // 字体需要向高位移动y次
            B0 = fontHZ[i] << offset;         
            B1 = (fontHZ[i] >> (8-offset))  |  ( fontHZ[i+1] << offset);
            B2 = (fontHZ[i+1] >> (8-offset));
            
            data[beginBrow][x] |=B0;
                                    
            // 超出部分隐藏
            if( beginBrow < 3)
                data[beginBrow+1][x] |=B1;  
            if( beginBrow < 2)
                data[beginBrow+2][x] |=B2;
            
            x++;
        }
    }else{     // 整数行，直接输出到对应字节
        for (int i = 0; i < 30; i+=2)
        {
            if(x>127)  // 超出部分隐藏
                continue;
            
            data[beginBrow][x] = fontHZ[i];  
            if( beginBrow < 3)
                data[beginBrow+1][x] = fontHZ[i+1];
            x++;
        }
    }
}   
void  PutFont8x16ToBuff(uint8_t x, uint8_t y, uint8_t* fontHZ)
{
    // y: 1-7 需要移位存到B0，B1，B2三个
    // y: 9-15,需要移位存到B1，B2，B3
    // y：0或者16，直接存B0、B1或者B2、B3
    // y>16，存不下，是否需要循环存放？超出的部分，移位存入B0 大于24时还要存入B1
    uint8_t brow = y;
    
    uint8_t offset;
    
    // 假设目标位置为（0，2）-（0,18），B0计算= 2/8 = 0;
    uint8_t beginBrow = y /8;
    uint8_t B0, B1, B2;   // 字库新的位置。B0对应 data[beginBrow][x], B1=data[beginBrow+1][0], B2=data[beginBrow+2][0];
    
    offset = y % 8;
    if(offset)   // 非整数行时，移位
    {
        for (int i = 0; i < 16; i+=2)
        {                
            if(x>127)  
                continue;
            // 字体需要向高位移动y次
            B0 = fontHZ[i] << offset;         
            B1 = (fontHZ[i] >> (8-offset))  |  ( fontHZ[i+1] << offset);
            B2 = (fontHZ[i+1] >> (8-offset));
            
            data[beginBrow][x] |=B0;
                                    
            // 超出部分隐藏
            if( beginBrow < 3)
                data[beginBrow+1][x] |=B1;  
            if( beginBrow < 2)
                data[beginBrow+2][x] |=B2;
            
            x++;
        }
    }else{     // 整数行，直接输出到对应字节
        for (int i = 0; i < 16; i+=2)
        {
            if(x>127)  // 超出部分隐藏
                continue;
            
            data[beginBrow][x] = fontHZ[i];  
            if( beginBrow < 3)
                data[beginBrow+1][x] = fontHZ[i+1];
            x++;
        }
    }
}     
void  PutFont7x8ToBuff(uint8_t x, uint8_t y, uint8_t* font)
{
    // y: 1-7 需要移位存到B0，B1，B2三个
    // y: 9-15,需要移位存到B1，B2，B3
    // y：0或者16，直接存B0、B1或者B2、B3
    // y>16，存不下，是否需要循环存放？超出的部分，移位存入B0 大于24时还要存入B1
    uint8_t brow = y;
    
    uint8_t offset;
    
    // 假设目标位置为（0，2）-（0,18），B0计算= 2/8 = 0;
    uint8_t beginBrow = y /8;
    uint8_t B0, B1, B2;   // 字库新的位置。B0对应 data[beginBrow][x], B1=data[beginBrow+1][0], B2=data[beginBrow+2][0];
    
    offset = y % 8;
    if(offset)   // 非整数行时，移位
    {
        for (int i = 0; i < 7; i++)
        {                
            if(x>127)  
                continue;
            // 字体需要向高位移动y次
            B0 = font[i] << offset;         
            B1 = font[i] >> (8-offset);
            
            data[beginBrow][x] |=B0;
                                    
            // 超出部分隐藏
            if( beginBrow < 3)
                data[beginBrow+1][x] |=B1;  
            
            x++;
        }
    }else{     // 整数行，直接输出到对应字节
        for (int i = 0; i < 7; i++)
        {
            if(x>127)  // 超出部分隐藏
                continue;
            
            data[beginBrow][x] = font[i];  
            x++;
        }
    }
}   
void  PutFont5x7ToBuff(uint8_t x, uint8_t y, uint8_t* font)
{
    // 5x7字体，高度7，
    // y=0时，直接放，y=1时，左移1位。y=2时，左移2位，跨2个字节。y=3，左移3位，跨2个字节。
    // y=8时，直接放，y=9时，左移1位
    uint8_t offset;  // 根据y是否是大行起始位置，决定是否移位。若y %8 >1, 跨2个大行
    
    // 假设目标位置为（0，2）-（0,18），B0计算= 2/8 = 0;
    uint8_t beginBrow = y /8;
    uint8_t B0, B1, B2;   // 字库新的位置。B0对应 data[beginBrow][x], B1=data[beginBrow+1][0], B2=data[beginBrow+2][0];
    
    offset = y % 8;  // 
    
    
    if(offset == 0)
    {   
        // 整数行，直接输出到对应字节
        for (int i = 0; i < 5; i++)
        {
            if(x>127)  // 超出部分隐藏
                continue;
            
            data[beginBrow][x] = font[i];  
            x++;
        }
        
    }
    else if(offset == 1)     // 一个大行完成
    {
        for (int i = 0; i < 5; i++)
        {                
            if(x>127)  
                continue;
            
            // 字体需要向高位移动y次
            B0 = font[i] << 1; 
            data[beginBrow][x] |=B0;
            
            x++;
        }
    }
    else   // 跨2个大行
    {  
        for (int i = 0; i < 5; i++)
        {                
            if(x>127)  
                continue;
            
            // 字体需要向高位移动y次
            B0 = font[i] << offset;         
            B1 = font[i] >> (8-offset);
            
            data[beginBrow][x] |=B0;
                                    
            // 超出部分隐藏
            if( beginBrow < 3)
                data[beginBrow+1][x] |=B1;  
            
            x++;
        }
    }
}
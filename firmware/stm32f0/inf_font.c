//字库芯片接口层文件 
#include "inf_font.h"  
#include "string.h"  
  
//字体数量 
#define FONT_NUM                    5  
  
//字体结构 
static struct _Font_Type Font_Type[FONT_NUM];  
//初始化字体类型 
static void init_font_type(void);  
  
/********************************************************************* 
*得到地址 
*参数:font:字体 
*     ch:待读取的字符 
*返回:地址 
**********************************************************************/  
  
static uint32_t get_address(uint8_t font,uint16_t ch);  
  
/********************************************************************* 
*得到字体地址 
*参数:ch1:字符编码第1个字节 
*     ch2:字符编码第2个字节 
*     ch3:字符编码第3个字节 
*     ch4:字符编码第4个字节 
*返回:地址 
**********************************************************************/  
  
static uint32_t get_address_GB18030_12X12(uint8_t c1,uint8_t c2,uint8_t c3,uint8_t c4);  
  
/********************************************************************* 
*得到字体地址 
*参数:ch1:字符编码第1个字节 
*     ch2:字符编码第2个字节 
*     ch3:字符编码第3个字节 
*     ch4:字符编码第4个字节 
*返回:地址 
**********************************************************************/  
  
static uint32_t get_address_GB18030_16X16(uint8_t c1,uint8_t c2,uint8_t c3,uint8_t c4);  
 
//初始化字库芯片 
void inf_font_init(void)  
{  
    //初始化字库芯片  
    drv_font_init();  
    //初始化字体类型  
    init_font_type();  
}  
  
/********************************************************************* 
*读取字库 
*参数:font:字体 
*     ch:待读取的字符 
*     buf:读取的数据 
*返回:读取数据的字节数 
**********************************************************************/  
  
uint8_t inf_font_read(uint8_t font,uint16_t ch,uint8_t *buf)  
{  
    uint32_t address = 0;  
    uint8_t i = 0;  
    uint8_t ch1 = ch >> 8;  
    uint8_t ch2 = ch;  
      
    //开始读取  
    drv_font_enable();  
    drv_font_send_byte(0x03);  
      
    //得到地址  
    address = get_address(font,ch);  
      
    //读取数据  
    drv_font_send_byte(address >> 16);  
    drv_font_send_byte(address >> 8);  
    drv_font_send_byte(address);  
    for (i = 0;i < Font_Type[font].size;i++)  
    {  
        buf[i] = drv_font_send_byte(0);  
    }  
      
    //关闭读取  
    drv_font_disable();  
}  
  
/********************************************************************* 
*将ASCII码转换成GB18030编码 
*说明:在emwin中调用中文字库,如果其中有ascii码,则必须先调用此函数转换 
*参数:dst:输入字符串 
*     src:输出字符串 
**********************************************************************/  
  
void inf_font_asc2gb18030(char *dst,char *src)  
{  
    uint8_t len = strlen(src);  
    uint8_t i = 0;  
    uint8_t j = 0;  
    uint16_t temp = 0;  
      
    for (i = 0;i < len;i++)  
    {  
        if ((uint8_t)src[i] < 0x80 && (uint8_t)src[i] != 0)  
        {  
            temp = (uint8_t)src[i] + 0xa380;  
            dst[j++] = temp >> 8;  
            dst[j++] = temp;  
        }  
        else  
        {  
            dst[j++] = src[i];  
        }  
    }  
}  
//初始化字体类型 
static void init_font_type(void)  
{  
    Font_Type[ASCII_7X8].addr_base = ASCII_7X8_ADDR_BASE;  
    Font_Type[ASCII_7X8].width = ASCII_7X8_WIDTH;  
    Font_Type[ASCII_7X8].height = ASCII_7X8_HEIGHT;  
    Font_Type[ASCII_7X8].size = ASCII_7X8_SIZE;  
      
    Font_Type[ASCII_BOLD_7X8].addr_base = ASCII_BOLD_7X8_ADDR_BASE;  
    Font_Type[ASCII_BOLD_7X8].width = ASCII_BOLD_7X8_WIDTH;  
    Font_Type[ASCII_BOLD_7X8].height = ASCII_BOLD_7X8_HEIGHT;  
    Font_Type[ASCII_BOLD_7X8].size = ASCII_BOLD_7X8_SIZE;  
      
    Font_Type[ASCII_6X12].addr_base = ASCII_6X12_ADDR_BASE;  
    Font_Type[ASCII_6X12].width = ASCII_6X12_WIDTH;  
    Font_Type[ASCII_6X12].height = ASCII_6X12_HEIGHT;  
    Font_Type[ASCII_6X12].size = ASCII_6X12_SIZE;  
      
    Font_Type[ASCII_8X16].addr_base = ASCII_8X16_ADDR_BASE;  
    Font_Type[ASCII_8X16].width = ASCII_8X16_WIDTH;  
    Font_Type[ASCII_8X16].height = ASCII_8X16_HEIGHT;  
    Font_Type[ASCII_8X16].size = ASCII_8X16_SIZE;  
      
    Font_Type[ASCII_BOLD_8X16].addr_base = ASCII_BOLD_8X16_ADDR_BASE;  
    Font_Type[ASCII_BOLD_8X16].width = ASCII_BOLD_8X16_WIDTH;  
    Font_Type[ASCII_BOLD_8X16].height = ASCII_BOLD_8X16_HEIGHT;  
    Font_Type[ASCII_BOLD_8X16].size = ASCII_BOLD_8X16_SIZE;  
      
    Font_Type[ASCII_12X24].addr_base = ASCII_12X24_ADDR_BASE;  
    Font_Type[ASCII_12X24].width = ASCII_12X24_WIDTH;  
    Font_Type[ASCII_12X24].height = ASCII_12X24_HEIGHT;  
    Font_Type[ASCII_12X24].size = ASCII_12X24_SIZE;  
      
    Font_Type[ASCII_16X32].addr_base = ASCII_16X32_ADDR_BASE;  
    Font_Type[ASCII_16X32].width = ASCII_16X32_WIDTH;  
    Font_Type[ASCII_16X32].height = ASCII_16X32_HEIGHT;  
    Font_Type[ASCII_16X32].size = ASCII_16X32_SIZE;  
      
    Font_Type[ASCII_BOLD_16X32].addr_base = ASCII_BOLD_16X32_ADDR_BASE;  
    Font_Type[ASCII_BOLD_16X32].width = ASCII_BOLD_16X32_WIDTH;  
    Font_Type[ASCII_BOLD_16X32].height = ASCII_BOLD_16X32_HEIGHT;  
    Font_Type[ASCII_BOLD_16X32].size = ASCII_BOLD_16X32_SIZE;  
      
    Font_Type[GB18030_12X12].addr_base = GB18030_12X12_ADDR_BASE;  
    Font_Type[GB18030_12X12].width = GB18030_12X12_WIDTH;  
    Font_Type[GB18030_12X12].height = GB18030_12X12_HEIGHT;  
    Font_Type[GB18030_12X12].size = GB18030_12X12_SIZE;  
      
    Font_Type[GB18030_16X16].addr_base = GB18030_16X16_ADDR_BASE;  
    Font_Type[GB18030_16X16].width = GB18030_16X16_WIDTH;  
    Font_Type[GB18030_16X16].height = GB18030_16X16_HEIGHT;  
    Font_Type[GB18030_16X16].size = GB18030_16X16_SIZE;  
      
    Font_Type[GB18030_24X24].addr_base = GB18030_24X24_ADDR_BASE;  
    Font_Type[GB18030_24X24].width = GB18030_24X24_WIDTH;  
    Font_Type[GB18030_24X24].height = GB18030_24X24_HEIGHT;  
    Font_Type[GB18030_24X24].size = GB18030_24X24_SIZE;  
}  
  
/********************************************************************* 
*得到地址 
*参数:font:字体 
*     ch:待读取的字符 
*返回:地址 
**********************************************************************/  
  
static uint32_t get_address(uint8_t font,uint16_t ch)   
{   
    uint32_t address = 0;  
    uint8_t ch1 = ch >> 8;  
    uint8_t ch2 = ch;  
      
    switch (font)  
    {  
        case ASCII_7X8:  
        case ASCII_BOLD_7X8:  
        case ASCII_6X12:  
        case ASCII_8X16:  
        case ASCII_BOLD_8X16:  
        case ASCII_12X24:  
        case ASCII_16X32:  
        {  
            address = Font_Type[font].addr_base + (ch - 0x20) * Font_Type[font].size;  
            break;  
        }  
        case ASCII_BOLD_16X32:  
        {  
            //芯片bug,弄反了几个符号的ascii  
            do  
            {  
                if (ch == ';')  
                {  
                    ch = ':';  
                    break;  
                }  
                if (ch == ':')  
                {  
                    ch = ';';  
                    break;  
                }  
                if (ch == '_')  
                {  
                    ch = '^';  
                    break;  
                }  
                if (ch == '^')  
                {  
                    ch = '_';  
                    break;  
                }  
            } while (0);  
            address = Font_Type[font].addr_base + (ch - 0x20) * Font_Type[font].size;  
            break;  
        }  
        case GB18030_12X12:  
        {  
            address = Font_Type[font].addr_base + get_address_GB18030_12X12(ch1,ch2,0,0) * Font_Type[font].size;  
            break;  
        }  
        case GB18030_16X16:  
        case GB18030_24X24:  
        {  
            address = Font_Type[font].addr_base + get_address_GB18030_16X16(ch1,ch2,0,0) * Font_Type[font].size;  
            break;  
        }  
    }  
}  
  

/********************************************************************* 
*得到字体地址 
*参数:ch1:字符编码第1个字节 
*     ch2:字符编码第2个字节 
*     ch3:字符编码第3个字节 
*     ch4:字符编码第4个字节 
*返回:地址 
**********************************************************************/  
  
static uint32_t get_address_GB18030_16X16(uint8_t c1,uint8_t c2,uint8_t c3,uint8_t c4)   
{   
    uint32_t h = 0;   
      
    if (c2 == 0x7f)   
    {  
        return h;   
    }  
      
    if (c1 >= 0xA1 && c1 <= 0xa9 && c2 >= 0xa1)  
    {  
        //Section 1   
        h = (c1 - 0xA1) * 94 + (c2 - 0xA1);   
    }  
    else   
    {  
        if (c1 >= 0xa8 && c1 <= 0xa9 && c2 < 0xa1)     
        {   
            //Section 5   
            if (c2 > 0x7f)   
            {                 
                c2--;    
            }                 
            h = (c1 - 0xa8) * 96 + (c2 - 0x40) + 846;     
        }  
    }    
      
    if (c1 >= 0xb0 && c1 <= 0xf7 && c2 >= 0xa1)        
    {  
        //Section 2   
        h = (c1 - 0xB0) * 94 + (c2 - 0xA1) + 1038;   
    }  
    else   
    {  
        if (c1 < 0xa1 && c1 >= 0x81 && c2 >= 0x40 )     
        {   
            //Section 3   
            if (c2 > 0x7f)    
            {  
                c2--;     
            }                 
            h = (c1 - 0x81) * 190 + (c2 - 0x40) + 1038 + 6768;   
        }   
        else   
        {  
            if(c1 >= 0xaa && c2 < 0xa1)                   
            {   
                //Section 4  
                if (c2 > 0x7f)    
                {  
                    c2--;   
                }                     
                h = (c1 - 0xaa) * 96 + (c2 - 0x40) + 1038 + 12848;   
            }   
            else  
            {  
                if(c1 == 0x81 && c2 >= 0x39)   
                {   
                    //四字节区1  
                    h = 1038 + 21008 + (c3 - 0xEE) * 10 + c4 - 0x39;   
                }   
                else  
                {  
                    if(c1 == 0x82)  
                    {   
                        //四字节区2  
                        h = 1038 + 21008 + 161 + (c2 - 0x30) * 1260 + (c3 - 0x81) * 10 + c4 - 0x30;   
                    }   
                }  
            }  
        }  
    }  
      
    return h;   
}  

/********************************************************************* 
*得到字体地址 
*参数:ch1:字符编码第1个字节 
*     ch2:字符编码第2个字节 
*     ch3:字符编码第3个字节 
*     ch4:字符编码第4个字节 
*返回:地址 
**********************************************************************/  
  
static uint32_t get_address_GB18030_12X12(uint8_t c1,uint8_t c2,uint8_t c3,uint8_t c4)   
{   
    uint32_t h = 0;   
      
    if (c2 == 0x7f)   
    {  
        return h;   
    }  
      
    if (c1 >= 0xA1 && c1 <= 0xa9 && c2 >= 0xa1)  
    {  
        //Section 1   
        h = (c1 - 0xA1) * 94 + (c2 - 0xA1);   
    }  
    else   
    {  
        if (c1 >= 0xa8 && c1 <= 0xa9 && c2 < 0xa1)     
        {   
            //Section 5   
            if (c2 > 0x7f)   
            {                 
                c2--;    
            }                 
            h = (c1 - 0xa8) * 96 + (c2 - 0x40) + 846;     
        }  
    }    
      
    if (c1 >= 0xb0 && c1 <= 0xf7 && c2 >= 0xa1)        
    {  
        //Section 2   
        h = (c1 - 0xB0) * 94 + (c2 - 0xA1) + 1038;   
    }  
    else   
    {  
        if (c1 < 0xa1 && c1 >= 0x81 && c2 >= 0x40 )     
        {   
            //Section 3   
            if (c2 > 0x7f)    
            {  
                c2--;     
            }                 
            h = (c1 - 0x81) * 190 + (c2 - 0x40) + 1038 + 6768;   
        }   
        else   
        {  
            if(c1 >= 0xaa && c2 < 0xa1)                   
            {   
                //Section 4  
                if (c2 > 0x7f)    
                {  
                    c2--;   
                }                     
                h = (c1 - 0xaa) * 96 + (c2 - 0x40) + 1038 + 12848;   
            }   
        }  
    }  
      
    return h;   
}  
  
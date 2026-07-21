//字库芯片驱动层文件     
#include "stm32f0xx_hal.h"
#include "drv_font.h"  

//初始化spi
static void init_spi(void);  
  
//初始化字库芯片 
void drv_font_init(void)  
{  
    //初始化spi  
    init_spi();  
}  

//打开SPI使能 
void drv_font_enable(void)  
{  
    GPIO_ResetBits(GPIOA, GPIO_Pin_4);  
}  
  
//关闭SPI使能 
void drv_font_disable(void)  
{  
    GPIO_SetBits(GPIOA, GPIO_Pin_4);  
}  
  
/********************************************************************* 
*spi发送一个字节 
*参数:dat:数据 
*返回:spi接收到的字节 
**********************************************************************/  
  
uint8_t drv_font_send_byte(uint8_t dat)  
{  
    while ((SPI1->SR & SPI_I2S_FLAG_TXE) == (uint16_t)RESET);  
    SPI1->DR = dat;  
    while ((SPI1->SR & SPI_I2S_FLAG_RXNE) == (uint16_t)RESET);  
    return (SPI1->DR);         
}  
  
//初始化spi 
static void init_spi(void)  
{  
    //定义IO初始化结构体  
    GPIO_InitTypeDef GPIO_InitStructure ;  
    //定义SPI初始化结构体  
    SPI_InitTypeDef  SPI_InitStructure ;  
  
    //配置CS  
    //初始化时钟  
    RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOA, ENABLE);  
    GPIO_PinAFConfig(GPIOA,GPIO_PinSource4,GPIO_AF_SPI1);  
    //管脚模式:输出口  
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;     
    //类型:推挽模式  
    GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;    
    //上拉下拉设置  
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;      
    //IO口速度  
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_100MHz;  
    //管脚指定  
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_4;  
    //初始化  
    GPIO_Init(GPIOA, &GPIO_InitStructure);  
    //关闭使能  
    drv_font_disable();  
  
    //初始化SPI  
    //关闭SPI  
    SPI_Cmd(SPI1,DISABLE);  
    //初始化SPI时钟    
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_SPI1,ENABLE);  
    //设置IO口时钟        
    RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOA, ENABLE);   
    GPIO_PinAFConfig(GPIOA,GPIO_PinSource5,GPIO_AF_SPI1);    
    GPIO_PinAFConfig(GPIOA,GPIO_PinSource6,GPIO_AF_SPI1);  
    GPIO_PinAFConfig(GPIOA,GPIO_PinSource7,GPIO_AF_SPI1);  
  
    //管脚模式:输出口  
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF;      
    //类型:推挽模式  
    GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;    
    //上拉下拉设置  
    GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_UP;      
    //IO口速度  
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_100MHz;  
    //管脚指定  
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_5 | GPIO_Pin_6 | GPIO_Pin_7;  
    //初始化  
    GPIO_Init(GPIOA, &GPIO_InitStructure);  
      
    // SPI配置  
    SPI_InitStructure.SPI_Direction = SPI_Direction_2Lines_FullDuplex ;  
    SPI_InitStructure.SPI_Mode = SPI_Mode_Master ;  
    SPI_InitStructure.SPI_DataSize = SPI_DataSize_8b ;  
    SPI_InitStructure.SPI_CPOL = SPI_CPOL_Low ;  
    SPI_InitStructure.SPI_CPHA = SPI_CPHA_1Edge ;  
    SPI_InitStructure.SPI_NSS = SPI_NSS_Soft ;  
    //SPI波特率分频设置  
    SPI_InitStructure.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_16 ;  
    //SPI设置成LSB模式  
    SPI_InitStructure.SPI_FirstBit = SPI_FirstBit_MSB ;  
    SPI_InitStructure.SPI_CRCPolynomial = 7 ;  
    SPI_Init( SPI1, &SPI_InitStructure ) ;  
  
    //启动SPI  
    SPI_Cmd(SPI1,ENABLE);  
}


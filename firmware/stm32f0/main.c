/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "stm32f0xx_hal.h"  
#include "GT20L_Font.h"
SPI_HandleTypeDef hspi1;          

TIM_HandleTypeDef htim14;

void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_TIM14_Init(void);
static void MX_SPI1_Init(void);

uint8_t ResetSCAN = 0;   
uint8_t aTxBuffer[16];
uint8_t aRxBuffer[32];   

 void delay13us()
{
	uint8_t i = 80;
	while (i--)
	{
		
	}
}            
void delay17us()
{
	uint8_t i = 106;
	while (i--)
	{
		
	}
}   
void delay3us()
{
	uint8_t i = 18;
	while (i--)
	{
		
	}
} 
void delay255ns()
{
	uint8_t i = 1;
	while (i--)
	{
		
	}
}       
#define 	 DelayUs          		__NOP();__NOP();__NOP();__NOP();      
#define		 LED_Set          		GPIOB->BSRR=1<<1               /*	PB1,PB2=1<<2     LED	*/       
#define 	 LED_Reset          		GPIOB->BRR=1<<1
#define		 Set_PA0          		GPIOA->BSRR=1<<0               /*	PA0,PB2=1<<2     	*/       
#define 	 Clr_PA0          		GPIOA->BRR=1<<0
#define		 SIN_Set          		GPIOA->BSRR=1<<1               /*	PA1,PB2=1<<2     SIN=PA1	*/       
#define 	 SIN_Reset          		GPIOA->BRR=1<<1
#define		 CLK_Set          		GPIOA->BSRR=1<<2               /*	PA2,PB2=1<<2     CLK=PA2	*/       
#define 	 CLK_Reset          		GPIOA->BRR=1<<2
#define		 LAT_Set          		GPIOA->BSRR=1<<3               /*	PA3,PB2=1<<2     LAT=PA3	*/       
#define 	 LAT_Reset          		GPIOA->BRR=1<<3
#define		 BK_Set          		GPIOA->BSRR=1<<4               /*	PA4,PB2=1<<2     BK=PA4	*/       
#define 	 BK_Reset          		GPIOA->BRR=1<<4
             
#define 	 SendDataH          		SIN_Set;CLK_Reset;CLK_Set;	// 输出H	
#define 	 SendDataL          		SIN_Reset;CLK_Reset;CLK_Set;	// 输出L          
               
#define		 PF0_Set          		GPIOF->BSRR=1<<0              /*	PF0, ef-ON	*/       
#define 	 PF0_Reset          	GPIOF->BRR=1<<0

#define		 PF1_Set          		GPIOF->BSRR=1<<1               /*	PF1, HV-EN	*/       
#define 	 PF1_Reset          	GPIOF->BRR=1<<1


#define		 Font_Disable           GPIOB->BSRR=1<<1               /*	PB1, 字库片选，低电平有效	*/       
#define 	 Font_Enable          	GPIOB->BRR=1<<1

#define     DUMMY_BYTE                  0xA5
  
uint8_t data[4][128] =
{
// 每行128个点。每字节对应一个垂直列的8个点，低位在上
{0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00},
{0x00,0x00,0x00,0x00,0xf0,0x10,0x10,0x10,0x10,0xff,0x10,0x10,0x10,0x10,0xf0,0x00,0x00,0x00,0x08,0x08,0x08,0x38,0xc8,0x08,0x09,0x0e,0x08,0x08,0xc8,0x38,0x08,0x08,0x08,0x00,0x10,0x60,0x02,0x8c,0x00,0xfe,0x02,0xf2,0x02,0xfe,0x00,0xf8,0x00,0xff,0x00,0x00,0x40,0x40,0x42,0xcc,0x00,0x90,0x90,0x90,0x90,0x90,0xff,0x10,0x11,0x16,0x10,0x00,0x20,0x20,0x20,0x20,0x20,0x20,0x20,0xff,0x20,0x20,0x20,0x20,0x20,0x20,0x20,0x00,0x00,0x00,0x00,0xe0,0x00,0x00,0x00,0xff,0x00,0x00,0x00,0x20,0x40,0x80,0x00,0x00,0x00,0x00,0x10,0x10,0x98,0xa4,0x47,0x44,0xa4,0x54,0x0c,0x04,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x60,0x18,0x00,0x00,0xff,0x00,0x00,0x08,0x90,0x20,0xc0},
{0x00,0x00,0x00,0x00,0x0f,0x04,0x04,0x04,0x04,0xff,0x04,0x04,0x04,0x04,0x0f,0x00,0x00,0x00,0x80,0x80,0x40,0x40,0x20,0x11,0x0a,0x04,0x0a,0x11,0x20,0x40,0x40,0x80,0x80,0x00,0x04,0x04,0x7e,0x01,0x80,0x47,0x30,0x0f,0x10,0x27,0x00,0x47,0x80,0x7f,0x00,0x00,0x00,0x00,0x00,0x3f,0x10,0x28,0x60,0x3f,0x10,0x10,0x01,0x0e,0x30,0x40,0xf0,0x00,0x80,0x80,0x40,0x20,0x10,0x0c,0x03,0x00,0x03,0x0c,0x10,0x20,0x40,0x80,0x80,0x00,0x08,0x04,0x03,0x00,0x00,0x40,0x80,0x7f,0x00,0x00,0x00,0x00,0x00,0x01,0x0e,0x00,0x00,0x81,0x89,0x89,0x44,0x44,0x4a,0x31,0x21,0x11,0x09,0x05,0x03,0x00,0x00,0x00,0x00,0x81,0x80,0x80,0x40,0x40,0x20,0x13,0x08,0x04,0x02,0x01,0x00,0x00},
{0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00}

};
  
uint8_t i=0,j=0,k=0, b,gp,test2=0;     
uint8_t g=0,cg=1; // cg 从1-43 
uint8_t sendBits=0;
    
uint32_t countHV, countHV2;  // 480khz 计数43次，折算为71.5hz, 占空比2%         
uint8_t ResetHVCount=200;



// 字库支持
extern uint8_t font5x7[4][5];
extern uint8_t font7x8[4][7];
extern uint8_t font8x16[4][16];
extern uint8_t font15x16[4][30];
                                  
uint32_t Get_Address15x16(uint8_t *text)
{
    uint8_t MSB = text[0]; 
    uint32_t address = 0;    
    uint32_t BaseAdd = 0;
    
    if(MSB> 0x7F) // >127是中文
    {
        uint8_t LSB = text[1];

        // 16x16国标字库标注6763个地址
        if (MSB == 0xA9 && LSB >= 0xA1)
            address = (282 + (LSB - 0xA1)) * 32 + BaseAdd;
        else if (MSB >= 0xA1 && MSB <= 0xA3 && LSB >= 0xA1)
            address = ((MSB - 0xA1) * 94 + (LSB - 0xA1)) * 32 + BaseAdd;
        else if (MSB >= 0xB0 && MSB <= 0xF7 && LSB >= 0xA1)
            address = ((MSB - 0xB0) * 94 + (LSB - 0xA1) + 846) * 32 + BaseAdd;
    }
    
    return address;
} 
//8X16 点国标扩展字符地址计算                                  
uint32_t Get_Address8x16(uint8_t *text)
{
    uint8_t MSB = text[0];   
    uint8_t LSB = text[1];
    
    uint32_t FontCode = LSB | ( MSB<< 8);
    uint32_t ByteAddress = 0;              
    uint32_t BaseAdd = 0x3b7d0;
    
    if ((FontCode >= 0xAAA1) && (FontCode <= 0xAAFE))
        ByteAddress = (FontCode - 0xAAA1 ) *16 + BaseAdd;
    else if ((FontCode >= 0xABA1) && (FontCode <= 0xABC0) )
        ByteAddress = (FontCode-0xABA1 + 95) *16 + BaseAdd;
    
    return ByteAddress;
}

// 读出的数据存放在aRxBuffer中，15X16是32个字节
uint8_t Font_Read(uint8_t font,uint16_t ch)  
{  
    
    // 字库芯片
    // step1. 首先把片选信号（CS#）变为低，紧跟着的是1 个字节的命令字（03 h）和3 个字节的地址和通
    // 过串行数据输入引脚（SI）移位输入，每一位在串行时钟（SCLK）上升沿被锁存。
    
    // step2. 然后该地址的字节数据通过串行数据输出引脚（SO）移位输出，每一位在串行时钟（SCLK）下降沿被移出。
    
    // step3. 读取字节数据后，则把片选信号（CS#）变为高，结束本次操作。
    
                                      
    uint32_t address = 0;    
    address = Get_Address15x16("啊");
    // step1:
    Font_Enable; // 字库片选        
    
    aTxBuffer[0] = 0x03;         
    aTxBuffer[1] = address >> 16;        // 24bit地址，MSB在前 
    aTxBuffer[2] = address >> 8; 
    aTxBuffer[3] = address; 
    HAL_SPI_Transmit(&hspi1, aTxBuffer, 4, 1000);  

    // step2:
    HAL_SPI_Receive(&hspi1, aRxBuffer,32,100);
    
    // step3:
    Font_Disable;
}  

uint8_t Font_FastRead(uint8_t font,uint16_t ch, uint8_t *buf)  
{  
    uint32_t address = 0; 
    address = Get_Address8x16("A");//Get_Address15x16("啊");
    
    // 字库芯片
    // step1. 首先把片选信号（CS#）变为低，紧跟着的是1 个字节的命令字（0B h）和3 个字节的地址以及
    //  一个字节 Dummy Byte 通过串行数据输入引脚（SI）移位输入，每一位在串行时钟（SCLK）上升沿被锁存。
    
    // step2. 然后该地址的字节数据通过串行数据输出引脚（SO）移位输出，每一位在串行时钟（SCLK）下降沿被移出。
    
    // step3. 读取字节数据后，则把片选信号（CS#）变为高，结束本次操作。
    
    
    // step1:
    Font_Enable; // 字库片选   
    
    aTxBuffer[0] = 0x08;      //    
    aTxBuffer[1] = address >> 16;        // 24bit地址，MSB在前 
    aTxBuffer[2] = address >> 8; 
    aTxBuffer[3] = address;     
    aTxBuffer[4] = 0xA5;//Dummy_Byte 任意值; 
    HAL_SPI_Transmit(&hspi1, aTxBuffer, 5, 1000);  

    // step2:
    HAL_SPI_Receive(&hspi1, aRxBuffer,32,100);
    
    // step3:
    Font_Disable;
}  
int main(void)
{

    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM14_Init();
    MX_SPI1_Init();


             
    BK_Set;	// 启动BK 
  
    //buff[i][j] = 0;
  
  for(i=0;i<4;i++)
  {
      for(j=0;j<2;j++)
      {
           
      }
  }  
                 
    HAL_Delay(20);
   
    cg = 1; 
  
  
  
  
  
    
    // 清空区域，填充测试字库   
    for(i=0;i<4;i++)
    {
      for(j=0;j<60;j++)
      {
           data[i][j] = 0;
      }
    }
    PutFont15x16ToBuff(0, 1, font15x16[1]);   //x:0-127, y:0-31。 字体，中飞扬
    PutFont8x16ToBuff(17, 0, font8x16[0]);   //x:0-127, y:0-31。 字体，abcd
    PutFont8x16ToBuff(17, 13, font8x16[1]);   //x:0-127, y:0-31。 字体，abcd
    PutFont5x7ToBuff(28, 0, font5x7[0]);   //x:0-127, y:0-31。 字体，abcd
    PutFont5x7ToBuff(33, 0, font5x7[1]);   //x:0-127, y:0-31。 字体，abcd
    PutFont5x7ToBuff(28, 10, font5x7[2]);   //x:0-127, y:0-31。 字体，abcd
    PutFont5x7ToBuff(33, 10, font5x7[3]);   //x:0-127, y:0-31。 字体，abcd
  
    uint8_t b1, b2, b3, brow;
	uint8_t row = 0;        
    PF0_Set;
    HAL_Delay(20); // 20ms延迟后开启HV， 71.5hz 占空比2%   
    HAL_TIM_Base_Start_IT(&htim14); 
    
    
    //Font_Read(1,'啊');
         
    Font_FastRead(1, '啊', aRxBuffer);
    while(1)
    {
        if(ResetSCAN)
        {
            ResetSCAN=0;           
            
			BK_Set;	// 启动BK 
			delay17us();
			LAT_Set;	// 17us后启动LAT启动LAT
			delay3us();
			LAT_Reset;  //3us后拉低LAT
			delay255ns();
			BK_Reset;  // display off, after 0.25us后发送数据
			
			delay13us();
   
//            for(i=0;i<32;i++)
//            {   
//                if(cg%2>0)
//                {             
//                    SendDataH;
//                    SendDataL;
//                    SendDataH;
//                    //SendDataH;
//                    SendDataL;
//                    SendDataH;
//                    SendDataL; 
//                } else{        
//                    SendDataL;
//                    SendDataH;
//                    SendDataL;
//                    SendDataL;
//                    SendDataL; 
//                    SendDataH;
//                }
//                
//            }      
            
            for (row = 0,brow=0; row < 32; row++)
            {
                if(row % 8 == 0)
                {
                    b1 = data[brow][(cg - 1) * 3 + 0];
                    b2 = data[brow][(cg - 1) * 3 + 1];

                    if(cg == 43)                      
                        b3 = 0; // 最后一列无数据了，129列
                    else       
                        b3 = data[brow][(cg - 1) * 3 + 2];
                    
                    brow++;
                }
                else
                {
                    // 非大行开始位置，逐渐左移（低位在前，所以右移取当前行）
                    b1 >>= 1;
                    b2 >>= 1;
                    b3 >>= 1;
                }    
                
                if(cg%2>0)
                {        
                     if (b1 & 0x01) {
                        SendDataH;
                    }
                    else {
                        SendDataL;
                    }

                    SendDataL;

                    if (b2 & 0x01) {
                        SendDataH;
                    }
                    else {
                        SendDataL;
                    }

                    SendDataL;

                    if (b3 & 0x01) {
                        SendDataH;
                    }
                    else {
                        SendDataL;
                    }

                    SendDataL;
                    
                } else{        
                    SendDataL;

                    if (b3 & 0x01) {
                        SendDataH;
                    }
                    else {
                        SendDataL;
                    }

                    SendDataL;

                    if (b2 & 0x01) {
                        SendDataH;
                    }
                    else {
                        SendDataL;
                    }

                    SendDataL;

                    if (b1 & 0x01) {
                        SendDataH;
                    }
                    else {
                        SendDataL;
                    }
                }
            }            
            delay13us();        
            
            
            for(g=0;g<48;g++)
            {      
                if(g == cg-1 || g== cg)
                {
                    SendDataH;	
                }else
                {
                    SendDataL ;
                }
            }   
            cg++;  // 当前grid列，1-43
            if(cg==44)        
            {
                cg = 1;
                ResetHVCount = 2;
                // HV开启直到  ResetHVCount递减到0
                PF1_Set;
            }    
            
            if(ResetHVCount--==1)
            {
                // ResetHVCount递减到0后关闭      
                PF1_Reset;
            }
            
        }
    } // end of while
    
}                










/** System Clock Configuration
*/
void SystemClock_Config(void)
{

  RCC_OscInitTypeDef RCC_OscInitStruct;
  RCC_ClkInitTypeDef RCC_ClkInitStruct;

    /**Initializes the CPU, AHB and APB busses clocks 
    */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = 16;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL12;
  RCC_OscInitStruct.PLL.PREDIV = RCC_PREDIV_DIV1;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    _Error_Handler(__FILE__, __LINE__);
  }

    /**Initializes the CPU, AHB and APB busses clocks 
    */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    _Error_Handler(__FILE__, __LINE__);
  }

    /**Configure the Systick interrupt time 
    */
  HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq()/1000);

    /**Configure the Systick 
    */
  HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);

  /* SysTick_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);
}

/* SPI1 init function */
static void MX_SPI1_Init(void)
{

  /* SPI1 parameter configuration*/
  hspi1.Instance = SPI1;
  hspi1.Init.Mode = SPI_MODE_MASTER;
  hspi1.Init.Direction = SPI_DIRECTION_2LINES;
  hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
  hspi1.Init.CLKPolarity = SPI_POLARITY_HIGH;
  hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
  hspi1.Init.NSS = SPI_NSS_SOFT;
  hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;
  hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
  hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
  hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  hspi1.Init.CRCPolynomial = 7;
  hspi1.Init.CRCLength = SPI_CRC_LENGTH_DATASIZE;
  hspi1.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
  if (HAL_SPI_Init(&hspi1) != HAL_OK)
  {
    _Error_Handler(__FILE__, __LINE__);
  }

}

/* TIM14 init function */
static void MX_TIM14_Init(void)
{

  htim14.Instance = TIM14;
  htim14.Init.Prescaler = 100-1;
  htim14.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim14.Init.Period = 150-1;
  htim14.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim14.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim14) != HAL_OK)
  {
    _Error_Handler(__FILE__, __LINE__);
  }

}

/** Configure pins as 
        * Analog 
        * Input 
        * Output
        * EVENT_OUT
        * EXTI
*/
static void MX_GPIO_Init(void)
{


  GPIO_InitTypeDef GPIO_InitStruct;

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_3|GPIO_PIN_4, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET);

  /*Configure GPIO pins : PA1 PA2 PA3 PA4 */
  GPIO_InitStruct.Pin = GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_3|GPIO_PIN_4;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pin : PB1 */
  GPIO_InitStruct.Pin = GPIO_PIN_1;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
  
        
  /*Configure GPIO pins : PF0 PF1 */
  GPIO_InitStruct.Pin = GPIO_PIN_0|GPIO_PIN_1;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  HAL_GPIO_Init(GPIOF, &GPIO_InitStruct);

}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @param  None
  * @retval None
  */
void _Error_Handler(char * file, int line)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  while(1) 
  {
  }
  /* USER CODE END Error_Handler_Debug */ 
}

#ifdef USE_FULL_ASSERT

/**
   * @brief Reports the name of the source file and the source line number
   * where the assert_param error has occurred.
   * @param file: pointer to the source file name
   * @param line: assert_param error line source number
   * @retval None
   */
void assert_failed(uint8_t* file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
    ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */

}

#endif

/**
  * @}
  */ 

/**
  * @}
*/ 

/************************ (C) COPYRIGHT STMicroelectronics *****END OF FILE****/

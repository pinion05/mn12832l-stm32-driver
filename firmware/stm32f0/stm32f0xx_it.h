#ifndef STM32F0XX_IT_H
#define STM32F0XX_IT_H

void NMI_Handler(void);
void HardFault_Handler(void);
void SVC_Handler(void);
void PendSV_Handler(void);
void SysTick_Handler(void);
void TIM14_IRQHandler(void);

#endif

#ifndef TEST_TARGET_STM32F0XX_HAL_H
#define TEST_TARGET_STM32F0XX_HAL_H

#include <stdint.h>

typedef enum {
    HAL_OK = 0,
    HAL_ERROR = 1,
} HAL_StatusTypeDef;

typedef struct {
    volatile uint32_t BSRR;
    volatile uint32_t BRR;
} GPIO_TypeDef;

typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
} GPIO_InitTypeDef;

typedef struct {
    void *Instance;
    struct {
        uint32_t Prescaler;
        uint32_t CounterMode;
        uint32_t Period;
        uint32_t ClockDivision;
        uint32_t AutoReloadPreload;
    } Init;
} TIM_HandleTypeDef;

typedef struct {
    uint32_t OscillatorType;
    uint32_t HSIState;
    uint32_t HSICalibrationValue;
    struct {
        uint32_t PLLState;
        uint32_t PLLSource;
        uint32_t PLLMUL;
        uint32_t PREDIV;
    } PLL;
} RCC_OscInitTypeDef;

typedef struct {
    uint32_t ClockType;
    uint32_t SYSCLKSource;
    uint32_t AHBCLKDivider;
    uint32_t APB1CLKDivider;
} RCC_ClkInitTypeDef;

extern GPIO_TypeDef *GPIOA;
extern GPIO_TypeDef *GPIOF;

#define GPIO_PIN_0 (1u << 0)
#define GPIO_PIN_1 (1u << 1)
#define GPIO_PIN_2 (1u << 2)
#define GPIO_PIN_3 (1u << 3)
#define GPIO_PIN_4 (1u << 4)
#define GPIO_PIN_RESET 0u
#define GPIO_PIN_SET 1u
#define GPIO_MODE_OUTPUT_PP 1u
#define GPIO_NOPULL 0u
#define GPIO_SPEED_FREQ_HIGH 3u

#define RCC_OSCILLATORTYPE_HSI 1u
#define RCC_HSI_ON 1u
#define RCC_PLL_ON 1u
#define RCC_PLLSOURCE_HSI 1u
#define RCC_PLL_MUL12 12u
#define RCC_PREDIV_DIV1 1u
#define RCC_CLOCKTYPE_HCLK (1u << 0)
#define RCC_CLOCKTYPE_SYSCLK (1u << 1)
#define RCC_CLOCKTYPE_PCLK1 (1u << 2)
#define RCC_SYSCLKSOURCE_PLLCLK 2u
#define RCC_SYSCLK_DIV1 1u
#define RCC_HCLK_DIV1 1u
#define FLASH_LATENCY_1 1u
#define SYSTICK_CLKSOURCE_HCLK 1u

#define TIM14 ((void *)(uintptr_t)0x14u)
#define TIM_COUNTERMODE_UP 0u
#define TIM_CLOCKDIVISION_DIV1 0u
#define TIM_AUTORELOAD_PRELOAD_DISABLE 0u

#define SVC_IRQn 1
#define PendSV_IRQn 2
#define SysTick_IRQn 3
#define TIM14_IRQn 4

#define __HAL_RCC_GPIOA_CLK_ENABLE() ((void)0)
#define __HAL_RCC_GPIOF_CLK_ENABLE() ((void)0)
#define __HAL_RCC_SYSCFG_CLK_ENABLE() ((void)0)
#define __HAL_RCC_TIM14_CLK_ENABLE() ((void)0)
#define __HAL_RCC_TIM14_CLK_DISABLE() ((void)0)

static inline uint32_t __get_PRIMASK(void)
{
    return 0u;
}

static inline void __disable_irq(void)
{
}

static inline void __enable_irq(void)
{
}

static inline void __NOP(void)
{
    __asm__ volatile("nop");
}

void HAL_Init(void);
void HAL_Delay(uint32_t milliseconds);
HAL_StatusTypeDef HAL_RCC_OscConfig(RCC_OscInitTypeDef *configuration);
HAL_StatusTypeDef HAL_RCC_ClockConfig(
    RCC_ClkInitTypeDef *configuration,
    uint32_t latency);
uint32_t HAL_RCC_GetHCLKFreq(void);
void HAL_SYSTICK_Config(uint32_t ticks);
void HAL_SYSTICK_CLKSourceConfig(uint32_t source);
void HAL_NVIC_SetPriority(int interrupt, uint32_t preempt, uint32_t subpriority);
void HAL_NVIC_EnableIRQ(int interrupt);
void HAL_NVIC_DisableIRQ(int interrupt);
void HAL_GPIO_WritePin(GPIO_TypeDef *port, uint32_t pins, uint32_t level);
void HAL_GPIO_Init(GPIO_TypeDef *port, GPIO_InitTypeDef *configuration);
HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef *timer);
HAL_StatusTypeDef HAL_TIM_Base_Start_IT(TIM_HandleTypeDef *timer);
void HAL_TIM_IRQHandler(TIM_HandleTypeDef *timer);
void HAL_IncTick(void);
void HAL_SYSTICK_IRQHandler(void);

void HAL_MspInit(void);
void HAL_TIM_Base_MspInit(TIM_HandleTypeDef *timer);
void HAL_TIM_Base_MspDeInit(TIM_HandleTypeDef *timer);

#endif

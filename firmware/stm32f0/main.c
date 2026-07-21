#include "main.h"

#include <stdbool.h>
#include <stddef.h>
#include <string.h>

#include "GT20L_Font.h"
#include "demo_fonts.h"
#include "vfd_delay.h"
#include "vfd_scan.h"

#define VFD_SIN_PIN GPIO_PIN_1
#define VFD_CLK_PIN GPIO_PIN_2
#define VFD_LAT_PIN GPIO_PIN_3
#define VFD_BLK_PIN GPIO_PIN_4
#define VFD_EF_PIN GPIO_PIN_0
#define VFD_HV_PIN GPIO_PIN_1

TIM_HandleTypeDef htim14;
volatile uint8_t vfd_scan_due;

static volatile bool vfd_gpio_ready;

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_TIM14_Init(void);

static inline void vfd_sin_set(void)
{
    GPIOA->BSRR = VFD_SIN_PIN;
}

static inline void vfd_sin_reset(void)
{
    GPIOA->BRR = VFD_SIN_PIN;
}

static inline void vfd_clk_set(void)
{
    GPIOA->BSRR = VFD_CLK_PIN;
}

static inline void vfd_clk_reset(void)
{
    GPIOA->BRR = VFD_CLK_PIN;
}

static inline void vfd_lat_set(void)
{
    GPIOA->BSRR = VFD_LAT_PIN;
}

static inline void vfd_lat_reset(void)
{
    GPIOA->BRR = VFD_LAT_PIN;
}

static inline void vfd_blank(void)
{
    GPIOA->BSRR = VFD_BLK_PIN;
}

static inline void vfd_unblank(void)
{
    GPIOA->BRR = VFD_BLK_PIN;
}

static inline void vfd_ef_enable(void)
{
    GPIOF->BSRR = VFD_EF_PIN;
}

static inline void vfd_ef_disable(void)
{
    GPIOF->BRR = VFD_EF_PIN;
}

static inline void vfd_hv_enable(void)
{
    GPIOF->BSRR = VFD_HV_PIN;
}

static inline void vfd_hv_disable(void)
{
    GPIOF->BRR = VFD_HV_PIN;
}

void VFD_SafeShutdown(void)
{
    if (!vfd_gpio_ready) {
        return;
    }

    /* Blank first, then remove the high-voltage and filament enables. */
    vfd_blank();
    vfd_hv_disable();
    vfd_ef_disable();
}

static bool vfd_scan_event_take(void)
{
    const uint32_t previous_mask = __get_PRIMASK();
    bool due;

    __disable_irq();
    due = vfd_scan_due != 0u;
    vfd_scan_due = 0u;
    if (previous_mask == 0u) {
        __enable_irq();
    }

    return due;
}

static void vfd_write_scan_bit(bool bit, void *context)
{
    (void)context;

    if (bit) {
        vfd_sin_set();
    } else {
        vfd_sin_reset();
    }
    vfd_clk_reset();
    vfd_clk_set();
}

static void vfd_pixel_grid_gap(void *context)
{
    (void)context;
    vfd_delay_13us_empirical();
}

static void vfd_latch_previous_frame(bool unblank_after_latch)
{
    vfd_blank();
    vfd_delay_17us_empirical();
    vfd_lat_set();
    vfd_delay_3us_empirical();
    vfd_lat_reset();
    vfd_delay_255ns_empirical();
    if (unblank_after_latch) {
        vfd_unblank();
    }
}

static void render_supplied_demo(void)
{
    /* Preserve the supplied background at x >= 60 and redraw its text area. */
    for (size_t page = 0; page < VFD_FONT_BUFFER_PAGES; ++page) {
        memset(data[page], 0, 60u * sizeof(data[page][0]));
    }

    PutFont15x16ToBuff(0u, 1u, font15x16[1]);
    PutFont8x16ToBuff(17u, 0u, font8x16[0]);
    PutFont8x16ToBuff(17u, 13u, font8x16[1]);
    PutFont5x7ToBuff(28u, 0u, font5x7[0]);
    PutFont5x7ToBuff(33u, 0u, font5x7[1]);
    PutFont5x7ToBuff(28u, 10u, font5x7[2]);
    PutFont5x7ToBuff(33u, 10u, font5x7[3]);
}

int main(void)
{
    VfdScanState scan_state;
    uint8_t scan_frame[VFD_SCAN_FRAME_BYTES];

    HAL_Init();
    MX_GPIO_Init();
    SystemClock_Config();
    MX_TIM14_Init();

    VFD_SafeShutdown();
    memset(scan_frame, 0, sizeof(scan_frame));
    if (!vfd_scan_emit_frame(
            scan_frame, vfd_write_scan_bit, vfd_pixel_grid_gap, NULL)) {
        _Error_Handler(__FILE__, (uint32_t)__LINE__);
    }
    vfd_latch_previous_frame(false);

    HAL_Delay(20u);
    render_supplied_demo();

    vfd_ef_enable();
    HAL_Delay(20u);

    vfd_scan_state_init(&scan_state);
    if (!vfd_scan_pack_step(data, scan_state.phase, scan_frame)) {
        _Error_Handler(__FILE__, (uint32_t)__LINE__);
    }
    if (HAL_TIM_Base_Start_IT(&htim14) != HAL_OK) {
        _Error_Handler(__FILE__, (uint32_t)__LINE__);
    }

    while (1) {
        if (!vfd_scan_event_take()) {
            continue;
        }

        vfd_latch_previous_frame(true);
        vfd_delay_13us_empirical();
        if (!vfd_scan_emit_frame(
                scan_frame, vfd_write_scan_bit, vfd_pixel_grid_gap, NULL)) {
            _Error_Handler(__FILE__, (uint32_t)__LINE__);
        }

        vfd_scan_state_advance(&scan_state);
        if (scan_state.hv_enabled) {
            vfd_hv_enable();
        } else {
            vfd_hv_disable();
        }

        if (!vfd_scan_pack_step(data, scan_state.phase, scan_frame)) {
            _Error_Handler(__FILE__, (uint32_t)__LINE__);
        }
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef oscillator = {0};
    RCC_ClkInitTypeDef clocks = {0};

    oscillator.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    oscillator.HSIState = RCC_HSI_ON;
    oscillator.HSICalibrationValue = 16u;
    oscillator.PLL.PLLState = RCC_PLL_ON;
    oscillator.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    oscillator.PLL.PLLMUL = RCC_PLL_MUL12;
    oscillator.PLL.PREDIV = RCC_PREDIV_DIV1;
    if (HAL_RCC_OscConfig(&oscillator) != HAL_OK) {
        _Error_Handler(__FILE__, (uint32_t)__LINE__);
    }

    clocks.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                       RCC_CLOCKTYPE_PCLK1;
    clocks.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clocks.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clocks.APB1CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clocks, FLASH_LATENCY_1) != HAL_OK) {
        _Error_Handler(__FILE__, (uint32_t)__LINE__);
    }

    HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq() / 1000u);
    HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);
    HAL_NVIC_SetPriority(SysTick_IRQn, 0u, 0u);
}

static void MX_TIM14_Init(void)
{
    htim14.Instance = TIM14;
    htim14.Init.Prescaler = 100u - 1u;
    htim14.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim14.Init.Period = 150u - 1u;
    htim14.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim14.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_Base_Init(&htim14) != HAL_OK) {
        _Error_Handler(__FILE__, (uint32_t)__LINE__);
    }
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef gpio = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();

    /* Preload the fail-safe levels before switching the pins to outputs. */
    HAL_GPIO_WritePin(
        GPIOA, VFD_SIN_PIN | VFD_CLK_PIN | VFD_LAT_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, VFD_BLK_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOF, VFD_EF_PIN | VFD_HV_PIN, GPIO_PIN_RESET);

    gpio.Pin = VFD_SIN_PIN | VFD_CLK_PIN | VFD_LAT_PIN | VFD_BLK_PIN;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOA, &gpio);

    gpio.Pin = VFD_EF_PIN | VFD_HV_PIN;
    HAL_GPIO_Init(GPIOF, &gpio);

    vfd_gpio_ready = true;
    VFD_SafeShutdown();
}

void _Error_Handler(const char *file, uint32_t line)
{
    (void)file;
    (void)line;

    __disable_irq();
    VFD_SafeShutdown();
    while (1) {
        __NOP();
    }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    _Error_Handler((const char *)file, line);
}
#endif

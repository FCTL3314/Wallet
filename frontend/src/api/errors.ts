export interface ApiError {
    code: string
    message: string
    detail?: string
}

export function isApiError(data: unknown): data is ApiError {
    return (
        typeof data === 'object' &&
        data !== null &&
        'code' in data &&
        'message' in data &&
        typeof (data as ApiError).code === 'string' &&
        typeof (data as ApiError).message === 'string'
    )
}

export function getErrorMessage(error: unknown): string {
    if (typeof error === 'object' && error !== null) {
        const axiosError = error as { response?: { data?: unknown } }
        const data = axiosError.response?.data

        if (isApiError(data)) {
            return data.message
        }

        // Legacy format fallback
        if (typeof data === 'object' && data !== null && 'detail' in data) {
            const detail = (data as { detail: unknown }).detail
            if (typeof detail === 'string') {
                return detail
            }
        }
    }
    return 'An unexpected error occurred'
}

export function getErrorCode(error: unknown): string | null {
    if (typeof error === 'object' && error !== null) {
        const axiosError = error as { response?: { data?: unknown } }
        const data = axiosError.response?.data
        if (isApiError(data)) {
            return data.code
        }
    }
    return null
}

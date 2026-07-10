import { get } from './client'

export interface ModelInfo {
  model_id: string
  input_price: number
  output_price: number
  type: 'text' | 'image'
}

export const listModels = () => get<ModelInfo[]>('/models')

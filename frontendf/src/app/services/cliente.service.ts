import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Cliente } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ClienteService {

  constructor(private apiService: ApiService) { }

  getClientes(params?: any): Observable<Cliente[]> {
    return this.apiService.get<Cliente[]>('/clientes/', params);
  }

  getCliente(id: number): Observable<Cliente> {
    return this.apiService.get<Cliente>(`/clientes/${id}/`);
  } 

  createCliente(payload: Cliente): Observable<Cliente> {
    return this.apiService.post<Cliente>('/crear-cliente/', payload);
  }

  updateCliente(id: number, payload: Cliente): Observable<Cliente>{
    return this.apiService.put<Cliente>(`/actualizar-cliente/${id}/`, payload);
  }

  deleteCliente(id: number): Observable<any> {
    return this.apiService.delete(`/eliminar-cliente/${id}/`);
  }

  importClientes(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.apiService.post<any>('/importar-clientes/', formData);
  }


}
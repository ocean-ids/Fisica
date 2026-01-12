import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Cliente } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ClienteService {

  constructor(private apiService: ApiService) { }

  getClientes(): Observable<Cliente[]> {
    return this.apiService.get<Cliente[]>('/clientes/');
  }

  getCliente(id: number): Observable<Cliente> {
    return this.apiService.get<Cliente>(`/clientes/${id}/`);
  } 

  CreateCliente(payload: Cliente): Observable<Cliente> {
    return this.apiService.post<Cliente>('/clientes/', payload);
  }

  updateCliente(id: number, payload: Cliente): Observable<Cliente>{
    return this.apiService.put<Cliente>(`/clientes/${id}/`, payload);
  }

  deleteCliente(id: number): Observable<any> {
    return this.apiService.delete(`/clientes/${id}/`);
  }
}
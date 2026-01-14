import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Persona } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PersonaService {

  constructor(private apiService: ApiService) { }

  getPersonas(): Observable<Persona[]> {
    return this.apiService.get<Persona[]>('/personas/');
  }

  getPersona(id: number): Observable<Persona> {
    return this.apiService.get<Persona>(`/personas/${id}/`);
  }

  createPersona(persona: Persona): Observable<Persona> {
    return this.apiService.post<Persona>('/crear-persona/', persona);
  }

  updatePersona(id: number, persona: Persona): Observable<Persona> {
    return this.apiService.put<Persona>(`/actualizar-persona/${id}/`, persona);
  }

  deletePersona(id: number): Observable<any> {
    return this.apiService.delete(`/personas/${id}/`);
  }
}

import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Asignacion } from '../../models/asignacion.model';
import { AsignacionService } from '../../services/asignacion.service';
import { Persona, Puesto } from '../../models';


@Component({
  selector: 'app-asignaciones',
  imports: [CommonModule, FormsModule],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent {
  asignaciones: Asignacion[] = [];
  personas: Persona[] = [];
  puestos: Puesto[] = [];
  filterredPuestos: Puesto[] = [];

}

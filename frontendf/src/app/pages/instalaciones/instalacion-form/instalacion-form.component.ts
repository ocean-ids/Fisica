import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { Cliente } from '../../../models/cliente.model';
import { ProvinciasService } from '../../../services/provincias.service';
import { Province, City } from '../../../data/provincias';

@Component({
  selector: 'app-instalacion-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule
  ],
  templateUrl: './instalacion-form.component.html',
  styleUrl: './instalacion-form.component.css'
})
export class InstalacionFormComponent implements OnInit {
  instalacionForm!: FormGroup;
  provincias: Province[] = [];
  ciudades: City[] = [];
  private initialCiudad: string | null = null;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<InstalacionFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { instalacion: any, clientes: Cliente[] }
    , private provinciasService: ProvinciasService
  ) {}

  ngOnInit(): void {
    const instalacion = this.data.instalacion || {};
    this.instalacionForm = this.fb.group({
      nombre: [instalacion.nombre || ''],
      cliente_id: [instalacion.cliente_id || '', Validators.required],
      provincia: [instalacion.provincia || '', Validators.required],
      ciudad: [instalacion.ciudad || '', Validators.required],
      codigo: [instalacion.codigo || ''],
      direccion: [instalacion.direccion || '']
    });

    this.provinciasService.getProvincias().subscribe(p => {
      this.provincias = p;
      // si estamos editando, recordar la ciudad para preservarla
      this.initialCiudad = instalacion.ciudad || null;
      const storedProv = instalacion.provincia;
      if (storedProv) {
        // intentar mapear la provincia guardada: puede ser el id o el nombre
        const provFound = this.provincias.find(x => x.id === storedProv || x.nombre.toLowerCase() === String(storedProv).toLowerCase());
        if (provFound) {
          // usar el id que espera el select
          this.instalacionForm.get('provincia')?.setValue(provFound.id);
        } else {
          // dejar el valor tal cual (fallback)
          this.instalacionForm.get('provincia')?.setValue(storedProv);
        }
        this.onProvinciaChange();
      }
    });
  }

  onProvinciaChange(): void {
    const provinciaId = this.instalacionForm.get('provincia')?.value;
    if (!provinciaId) {
      this.ciudades = [];
      this.instalacionForm.get('ciudad')?.setValue('');
      return;
    }
    this.provinciasService.getCiudadesPorProvincia(provinciaId).subscribe(c => {
      this.ciudades = c;
      // si venimos de edición y la ciudad inicial está en la lista, úsala (comparaciones case-insensitive)
      if (this.initialCiudad) {
        const search = String(this.initialCiudad).toLowerCase();
        const found = this.ciudades.find(x => (x.nombre && x.nombre.toLowerCase() === search) || (x.id && x.id.toLowerCase() === search));
        if (found) {
          this.instalacionForm.get('ciudad')?.setValue(found.nombre);
          this.initialCiudad = null; // usar solo una vez
          return;
        }
        this.initialCiudad = null;
      }
      // si la ciudad actual está en la nueva lista, conservarla (case-insensitive)
      const current = this.instalacionForm.get('ciudad')?.value;
      if (current && this.ciudades.find(x => (x.nombre && x.nombre.toLowerCase() === String(current).toLowerCase()) || (x.id && x.id.toLowerCase() === String(current).toLowerCase()))) {
        return;
      }
      // en caso contrario, asignar automáticamente la primera ciudad disponible
      if (this.ciudades.length > 0) {
        this.instalacionForm.get('ciudad')?.setValue(this.ciudades[0].nombre);
      } else {
        this.instalacionForm.get('ciudad')?.setValue('');
      }
    });
  }

  onSubmit(): void {
    if (this.instalacionForm.valid) {
      this.dialogRef.close(this.instalacionForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}

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
      cliente_id: [instalacion.cliente_id || '', Validators.required],
      provincia: [instalacion.provincia || '', Validators.required],
      ciudad: [instalacion.ciudad || '', Validators.required]
    });

    this.provinciasService.getProvincias().subscribe(p => {
      this.provincias = p;
      // si estamos editando, recordar la ciudad para preservarla
      this.initialCiudad = instalacion.ciudad || null;
      const prov = instalacion.provincia;
      if (prov) {
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
      // si venimos de edición y la ciudad inicial está en la lista, úsala
      if (this.initialCiudad) {
        const found = this.ciudades.find(x => x.nombre === this.initialCiudad || x.id === this.initialCiudad);
        if (found) {
          this.instalacionForm.get('ciudad')?.setValue(found.nombre);
          this.initialCiudad = null; // usar solo una vez
          return;
        }
        this.initialCiudad = null;
      }
      // si la ciudad actual está en la nueva lista, conservarla
      const current = this.instalacionForm.get('ciudad')?.value;
      if (current && this.ciudades.find(x => x.nombre === current || x.id === current)) {
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

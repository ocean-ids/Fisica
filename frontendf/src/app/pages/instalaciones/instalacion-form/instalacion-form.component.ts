import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { Cliente } from '../../../models/cliente.model';
import { UbicacionService } from '../../../services/ubicacion.service';
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
  provincias: (any | Province)[] = [];
  cantones: (any | City)[] = [];
  private useStaticProvincias = false;
  zonaOptions: { id: any; label: string; titulo?: string }[] = [];
  private defaultZonaTitles = ['Zona 1'];
  private zonaTitles = ['Zona 1', 'Zona 2', 'Zona 3'];
  
  private initialCanton: string | null = null;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<InstalacionFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { instalacion: any, clientes: Cliente[] },
    private ubicacionService: UbicacionService,
    private provinciasService: ProvinciasService
  ) {}

  ngOnInit(): void {
    const instalacion = this.data.instalacion || {};
    
    this.zonaOptions = this.zonaTitles.map(t => ({ id: t, titulo: t, label: t }));
    this.instalacionForm = this.fb.group({
      nombre: [instalacion.nombre || ''],
      cliente_id: [instalacion.cliente_id || '', Validators.required],
      provincia_id: [instalacion.provincia_id || '', Validators.required],
      canton_id: [instalacion.canton_id || '', Validators.required],
      direccion: [instalacion.direccion || ''],
      zona_id: [instalacion.zona_id || this.zonaOptions[0]?.id || null]
    });

    if (instalacion.zonas && Array.isArray(instalacion.zonas) && instalacion.zonas.length) {
      this.zonaOptions = this.withDefaultZonaTitles(this.buildZonaOptions(instalacion.zonas));
      this.instalacionForm.get('zona_id')?.setValue(this.zonaOptions[0]?.id || null);
    }

    if (instalacion.id) {
      this.ubicacionService.getZonas(instalacion.id).subscribe({
        next: zonas => {
          if (zonas && Array.isArray(zonas) && zonas.length) {
            this.zonaOptions = this.withDefaultZonaTitles(this.buildZonaOptions(zonas));
          } else {
            // instalaciones antiguas sin zonas: ofrecer Zona 1/2/3
            this.zonaOptions = this.zonaTitles.map(t => ({ id: t, titulo: t, label: t }));
          }
          this.instalacionForm.get('zona_id')?.setValue(this.zonaOptions[0]?.id || null);
        },
        error: () => {}
      });
    } else {
      // En creación, ofrece Zona 1/2/3 como títulos; backend creará solo la elegida
      this.zonaOptions = this.zonaTitles.map(t => ({ id: t, titulo: t, label: t }));
      this.instalacionForm.get('zona_id')?.setValue(this.zonaOptions[0]?.id || null);
    }

    this.loadProvincias(instalacion);
  }

  onProvinciaChange(): void {
    const provinciaId = this.instalacionForm.get('provincia_id')?.value;
    if (!provinciaId) {
      this.cantones = [];
      this.instalacionForm.get('canton_id')?.setValue('');
      return;
    }
    if (this.useStaticProvincias) {
      const prov = (this.provincias as Province[]).find(x => x.id === provinciaId);
      this.cantones = prov ? prov.ciudades : [];
      this.afterCantonesLoaded();
    } else {
      this.ubicacionService.getCantones(provinciaId).subscribe((cants: any[]) => {
        this.cantones = cants || [];
        this.afterCantonesLoaded();
      });
    }
  }

  private loadProvincias(instalacion: any): void {
    this.ubicacionService.getProvincias().subscribe({
      next: (p) => {
        this.provincias = p || [];
        this.useStaticProvincias = !p || !Array.isArray(p) || p.length === 0;
        if (this.useStaticProvincias) {
          this.provincias = this.provinciasService.getProvinciasSync();
        }
        this.initialCanton = instalacion.canton_id || null;
        const storedProv = instalacion.provincia_id;
        if (storedProv) {
          const provFound = this.provincias.find((x: any) => x.id === storedProv);
          if (provFound) {
            this.instalacionForm.get('provincia_id')?.setValue(provFound.id);
            this.onProvinciaChange();
          }
        }
      },
      error: () => {
        this.useStaticProvincias = true;
        this.provincias = this.provinciasService.getProvinciasSync();
      }
    });
  }

  private afterCantonesLoaded(): void {
    if (this.initialCanton) {
      const found = this.cantones.find((x: any) => x.id === this.initialCanton);
      if (found) {
        this.instalacionForm.get('canton_id')?.setValue(found.id);
        this.initialCanton = null;
        return;
      }
      this.initialCanton = null;
    }
    const current = this.instalacionForm.get('canton_id')?.value;
    if (current && this.cantones.find((x: any) => x.id === current)) {
      return;
    }
    if (this.cantones.length > 0) {
      this.instalacionForm.get('canton_id')?.setValue(this.cantones[0].id);
    } else {
      this.instalacionForm.get('canton_id')?.setValue('');
    }
  }

  private buildZonaOptions(zonas: any[]): { id: any; label: string; titulo?: string }[] {
    return zonas.map((z: any) => {
      const titulo = z?.titulo || '';
      const labelParts = [titulo || 'Zona'].filter(Boolean);
      return {
        id: z?.id ?? titulo,
        titulo,
        label: labelParts.join(' · ')
      };
    });
  }

  private withDefaultZonaTitles(options: { id: any; label: string; titulo?: string }[]): { id: any; label: string; titulo?: string }[] {
    const titles = new Set((options || []).map(o => (o.titulo || '').trim()).filter(Boolean));
    const merged = [...options];
    this.zonaTitles.forEach(t => {
      if (!titles.has(t)) {
        merged.push({ id: t, titulo: t, label: t });
      }
    });
    return merged;
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

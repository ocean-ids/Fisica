import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { Observable } from 'rxjs';
import { debounceTime, startWith, map } from 'rxjs/operators';
import { ClienteService } from '../../../services/cliente.service';
import { InstalacionService } from '../../../services/instalacion.service';
import { PuestoService } from '../../../services/puesto.service';
import { PersonaService } from '../../../services/persona.service';
import { Cliente, Instalacion } from '../../../models';
import { Puesto } from '../../../models/puesto.model';
import { Persona } from '../../../models/persona.model';
import { ReporteGuardia } from '../../../models/reporte-guardia.model';

interface DialogData {
  row?: ReporteGuardia;   // presente = edición
}

@Component({
  selector: 'app-crear-apoyo-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatSelectModule, MatAutocompleteModule, MatButtonModule,
  ],
  templateUrl: './crear-apoyo-dialog.component.html',
  styleUrl: './crear-apoyo-dialog.component.css',
})
export class CrearApoyoDialogComponent implements OnInit {
  clientes: Cliente[] = [];
  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];
  personasAll: Persona[] = [];
  clienteId: number | null = null;
  instalacionId: number | null = null;
  puestoId: number | null = null;
  personaCtrl = new FormControl<any>('');
  personasFiltradas$!: Observable<Persona[]>;
  personaSel: Persona | null = null;
  proviene = '';
  motivo = '';
  esEdicion = false;
  private editPersonaId: number | null = null;

  constructor(
    private ref: MatDialogRef<CrearApoyoDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private clienteSrv: ClienteService,
    private instalacionSrv: InstalacionService,
    private puestoSrv: PuestoService,
    private personaSrv: PersonaService,
  ) {}

  ngOnInit(): void {
    const row = this.data?.row;
    this.esEdicion = !!row?.id;
    if (row) {
      this.motivo = row.motivo || '';
      this.proviene = row.proviene || '';
      this.editPersonaId = (row as any).persona_ref ?? null;
      if (row.persona_nombre) { this.personaCtrl.setValue(row.persona_nombre); }
    }

    this.clienteSrv.getClientes().subscribe((cs) => {
      this.clientes = cs || [];
      if (row?.cliente) {
        const c = this.clientes.find(x => x.nombre_comercial === row.cliente);
        if (c) { this.clienteId = c.id!; this.onCliente(row.puesto); }
      }
    });

    // Cargar todas las personas y filtrar localmente (dropdown poblado + filtrable).
    this.personaSrv.getPersonas({}).subscribe((ps) => { this.personasAll = ps || []; });
    this.personasFiltradas$ = this.personaCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(120),
      map((val: any) => {
        const q = (typeof val === 'string' ? val : this.displayPersona(val)).toLowerCase().trim();
        if (!q) { return this.personasAll.slice(0, 50); }
        const tokens = q.split(/\s+/).filter(Boolean);
        return this.personasAll
          .filter(p => {
            const hay = `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''}`.toLowerCase();
            return tokens.every(t => hay.includes(t));
          })
          .slice(0, 50);
      }),
    );
  }

  // Cliente -> carga sus instalaciones. En edición, ubica el puesto para preseleccionar.
  onCliente(preselectPuestoNombre?: string): void {
    this.instalaciones = [];
    this.puestos = [];
    if (!preselectPuestoNombre) { this.instalacionId = null; this.puestoId = null; }
    if (!this.clienteId) { return; }
    this.instalacionSrv.getInstalaciones({ cliente_id: this.clienteId }).subscribe((is) => {
      this.instalaciones = is || [];
    });
    if (preselectPuestoNombre) {
      // Ubicar a qué instalación pertenece el puesto guardado para preseleccionar todo.
      this.puestoSrv.getPuestosPorCliente(this.clienteId).subscribe((ps) => {
        const p = (ps || []).find(x => x.nombre === preselectPuestoNombre);
        if (p) {
          this.instalacionId = p.instalacion_id ?? (p as any).instalacion ?? null;
          this.onInstalacion(preselectPuestoNombre);
        }
      });
    }
  }

  // Instalación -> carga sus puestos (se ve solo el nombre del puesto).
  onInstalacion(preselectPuestoNombre?: string): void {
    this.puestos = [];
    if (!preselectPuestoNombre) { this.puestoId = null; }
    if (!this.instalacionId) { return; }
    this.puestoSrv.getPuestosPorInstalacion(this.instalacionId).subscribe((ps) => {
      this.puestos = ps || [];
      if (preselectPuestoNombre) {
        const p = this.puestos.find(x => x.nombre === preselectPuestoNombre);
        if (p) { this.puestoId = p.id; }
      }
    });
  }

  displayPersona = (p: any): string => {
    if (!p) { return ''; }
    if (typeof p === 'string') { return p; }
    return `${p.nombres || ''} ${p.apellidos || ''}`.trim();
  };

  onPersonaSel(p: Persona): void {
    this.personaSel = p;
    this.proviene = p?.tipo || '';
  }

  get valido(): boolean {
    return !!this.clienteId && !!this.instalacionId && !!this.puestoId;
  }

  guardar(): void {
    const cli = this.clientes.find(c => c.id === this.clienteId);
    const pto = this.puestos.find(p => p.id === this.puestoId);
    const p = this.personaSel;
    const out: any = {
      cliente: cli?.nombre_comercial || '',
      puesto: pto?.nombre || '',            // solo el nombre del puesto
      motivo: (this.motivo || '').trim(),
    };
    if (p) {
      out.persona_nombre = `${p.nombres} ${p.apellidos}`.trim();
      out.persona_ref = p.id;
      out.proviene = p.tipo || '';
    } else {
      // Edición sin cambiar la persona: conservar la existente.
      out.persona_ref = this.editPersonaId;
      out.persona_nombre = typeof this.personaCtrl.value === 'string' ? this.personaCtrl.value : '';
      out.proviene = this.proviene || '';
    }
    this.ref.close(out);
  }

  cancelar(): void {
    this.ref.close();
  }
}

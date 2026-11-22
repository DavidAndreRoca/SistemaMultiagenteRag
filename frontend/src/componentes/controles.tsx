// Controles comunes sobre React Aria Components (decisión T13-01): etiquetas asociadas,
// mensajes de validación anunciados, foco visible y uso completo con teclado.
import type { ReactNode } from "react";
import {
  Button,
  FieldError,
  FileTrigger,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
  Text,
  TextArea,
  TextField,
  type ButtonProps,
  type Key,
  type TextFieldProps,
} from "react-aria-components";

import { ErrorApi } from "../api/cliente";

export function Boton({
  variante = "principal",
  className,
  ...props
}: ButtonProps & { variante?: "principal" | "secundario" }) {
  return (
    <Button
      {...props}
      className={["boton", `boton--${variante}`, typeof className === "string" ? className : ""]
        .join(" ")
        .trim()}
    />
  );
}

export function CampoTexto({
  etiqueta,
  descripcion,
  ...props
}: TextFieldProps & { etiqueta: string; descripcion?: string }) {
  return (
    <TextField {...props} className="campo">
      <Label>{etiqueta}</Label>
      <Input />
      {descripcion ? <Text slot="description">{descripcion}</Text> : null}
      <FieldError className="campo__error" />
    </TextField>
  );
}

export function CampoTextoLargo({
  etiqueta,
  descripcion,
  ...props
}: TextFieldProps & { etiqueta: string; descripcion?: string }) {
  return (
    <TextField {...props} className="campo">
      <Label>{etiqueta}</Label>
      <TextArea />
      {descripcion ? <Text slot="description">{descripcion}</Text> : null}
      <FieldError className="campo__error" />
    </TextField>
  );
}

export interface Opcion {
  id: string;
  etiqueta: string;
}

export function Selector({
  etiqueta,
  opciones,
  valor,
  alCambiar,
  requerido = false,
  marcador = "Elija una opción",
}: {
  etiqueta: string;
  opciones: Opcion[];
  valor: string | null;
  alCambiar: (valor: string | null) => void;
  requerido?: boolean;
  marcador?: string;
}) {
  return (
    <Select
      className="campo"
      value={valor}
      onChange={(clave: Key | null) => {
        alCambiar(clave === null ? null : String(clave));
      }}
      isRequired={requerido}
      placeholder={marcador}
    >
      <Label>{etiqueta}</Label>
      <Button className="selector__boton">
        <SelectValue />
        <span aria-hidden="true">▾</span>
      </Button>
      <FieldError className="campo__error" />
      <Popover className="selector__lista">
        <ListBox items={opciones}>
          {(opcion) => (
            <ListBoxItem id={opcion.id} className="selector__opcion">
              {opcion.etiqueta}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </Select>
  );
}

export function SelectorArchivo({
  etiqueta,
  tipos,
  archivo,
  alElegir,
}: {
  etiqueta: string;
  tipos: string[];
  archivo: File | null;
  alElegir: (archivo: File | null) => void;
}) {
  return (
    <div className="campo">
      <FileTrigger
        acceptedFileTypes={tipos}
        onSelect={(lista) => {
          alElegir(lista?.item(0) ?? null);
        }}
      >
        <Boton variante="secundario">{etiqueta}</Boton>
      </FileTrigger>
      <p className="campo__descripcion" aria-live="polite">
        {archivo ? `Archivo elegido: ${archivo.name}` : "Ningún archivo elegido."}
      </p>
    </div>
  );
}

/** Mensaje de error del formato común, con el identificador de incidencia si lo hay. */
export function AvisoError({ error }: { error: unknown }) {
  if (error === null || error === undefined) return null;
  const api = error instanceof ErrorApi ? error : null;
  return (
    <div className="aviso aviso--error" role="alert">
      <p>{api?.message ?? "Ocurrió un error inesperado."}</p>
      {api?.incidenciaId ? (
        <p className="aviso__incidencia">Identificador de incidencia: {api.incidenciaId}</p>
      ) : null}
    </div>
  );
}

export function AvisoInformativo({ children }: { children: ReactNode }) {
  return (
    <div className="aviso aviso--informativo" role="status">
      {children}
    </div>
  );
}

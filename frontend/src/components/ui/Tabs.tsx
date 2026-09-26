import * as RadixTabs from "@radix-ui/react-tabs";
import type { ComponentPropsWithoutRef } from "react";

import { cx } from "../../lib/cx";
import styles from "./ui.module.css";

export const Tabs = RadixTabs.Root;

export function TabsList({ className, ...rest }: ComponentPropsWithoutRef<typeof RadixTabs.List>): React.JSX.Element {
  return <RadixTabs.List className={cx(styles["tabsList"], className)} {...rest} />;
}

export function TabsTrigger({
  className,
  ...rest
}: ComponentPropsWithoutRef<typeof RadixTabs.Trigger>): React.JSX.Element {
  return <RadixTabs.Trigger className={cx(styles["tabsTrigger"], className)} {...rest} />;
}

export function TabsContent({
  className,
  ...rest
}: ComponentPropsWithoutRef<typeof RadixTabs.Content>): React.JSX.Element {
  return <RadixTabs.Content className={cx(styles["tabsContent"], className)} {...rest} />;
}
